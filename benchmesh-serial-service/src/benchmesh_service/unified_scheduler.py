"""
Unified Polling Scheduler

This module implements a centralized scheduler that coordinates polling
for all devices with per-device intervals and queue throttling.

Benefits:
- Per-device polling intervals (respects device capabilities)
- Queue depth throttling (prevents oversubscription)
- Circuit breaker for dead devices (prevents wasted polling)
- Better control over system load and timing

The scheduler triggers device workers by enqueuing LOW priority
polling requests at device-specific intervals.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, TYPE_CHECKING

from .priority_queue import DeviceRequestQueue, PollRequest, Priority

if TYPE_CHECKING:
    from .connection import DeviceConnection

logger = logging.getLogger(__name__)


class UnifiedScheduler:
    """
    Central polling scheduler for all devices.

    Coordinates polling of all devices by enqueuing polling requests
    at per-device intervals. Includes queue throttling and circuit breaker
    for dead devices to prevent oversubscription.

    Attributes:
        default_interval_ms: Default polling interval in milliseconds
        max_queue_depth: Maximum queue depth before throttling
        device_queues: Map of device_id -> DeviceRequestQueue
        device_connections: Map of device_id -> DeviceConnection (for health checks)
        device_intervals: Map of device_id -> interval_ms
        last_poll_time: Map of device_id -> timestamp of last poll enqueue
        skipped_polls: Counter for throttled polls per device
        running: Flag indicating if scheduler is active
        thread: Scheduler thread
    """

    def __init__(self, interval_ms: float = 50.0, max_queue_depth: int = 10, device_connections: Optional[Dict[str, 'DeviceConnection']] = None, registry=None):
        """
        Initialize unified scheduler.

        Args:
            interval_ms: Default polling interval in milliseconds (default 50ms = 20Hz)
            max_queue_depth: Maximum queue depth before throttling (default 10)
            device_connections: Map of device_id -> DeviceConnection for health checks
            registry: DeviceRegistry instance for clearing disconnected devices
        """
        self.default_interval_ms = interval_ms
        self.max_queue_depth = max_queue_depth
        self.device_queues: Dict[str, DeviceRequestQueue] = {}
        self.device_connections: Dict[str, 'DeviceConnection'] = device_connections or {}
        self.device_intervals: Dict[str, float] = {}
        self.last_poll_time: Dict[str, float] = {}
        self.skipped_polls: Dict[str, int] = {}
        self.registry = registry
        self.device_was_healthy: Dict[str, bool] = {}  # Track previous health state
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def register_device(self, device_id: str, queue: DeviceRequestQueue, interval_ms: Optional[float] = None) -> None:
        """
        Register a device for unified polling.

        Args:
            device_id: Unique device identifier
            queue: Priority queue for device requests
            interval_ms: Polling interval for this device (uses default if None)
        """
        with self._lock:
            self.device_queues[device_id] = queue
            self.device_intervals[device_id] = interval_ms if interval_ms is not None else self.default_interval_ms
            self.last_poll_time[device_id] = 0.0  # Start immediately
            self.skipped_polls[device_id] = 0
            self.device_was_healthy[device_id] = True  # Assume healthy initially
            logger.info(
                f"Unified scheduler: registered device {device_id} "
                f"with interval={self.device_intervals[device_id]}ms"
            )

    def unregister_device(self, device_id: str) -> None:
        """
        Unregister a device from unified polling.

        Args:
            device_id: Device identifier to remove
        """
        with self._lock:
            if device_id in self.device_queues:
                del self.device_queues[device_id]
                del self.device_intervals[device_id]
                del self.last_poll_time[device_id]
                del self.skipped_polls[device_id]
                logger.info(f"Unified scheduler: unregistered device {device_id}")

    def start(self) -> None:
        """
        Start the unified scheduler thread.

        The scheduler will run in the background, triggering device polls
        at per-device intervals until stop() is called.
        """
        if self.running:
            logger.warning("Unified scheduler already running")
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._scheduler_loop,
            name="unified-scheduler",
            daemon=True
        )
        self.thread.start()
        logger.info(
            f"Unified scheduler started (default_interval={self.default_interval_ms}ms, "
            f"max_queue_depth={self.max_queue_depth})"
        )

    def stop(self) -> None:
        """
        Stop the unified scheduler thread.

        Gracefully stops the scheduler, allowing current iteration to complete.
        """
        if not self.running:
            return

        logger.info("Stopping unified scheduler...")
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.1)  # 100ms timeout

        logger.info("Unified scheduler stopped")

    def _scheduler_loop(self) -> None:
        """
        Main scheduler loop.

        Runs continuously with a fast tick rate (10ms), checking each device
        individually to see if it's time to poll based on per-device intervals.
        Includes queue depth throttling to prevent oversubscription.
        """
        logger.info("Unified scheduler loop started")
        tick_interval_ms = 10.0  # Fast tick rate for checking devices
        next_tick_time = time.time()

        while self.running:
            try:
                # Calculate when this tick should complete
                next_tick_time += tick_interval_ms / 1000.0

                # Check and trigger devices individually
                self._check_and_trigger_devices()

                # Sleep until next tick (adaptive timing)
                now = time.time()
                sleep_time = next_tick_time - now

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    # Fell behind schedule - catch up
                    if sleep_time < -0.05:  # Only warn if >50ms behind
                        logger.warning(
                            f"Unified scheduler: fell behind by {-sleep_time*1000:.1f}ms, "
                            f"resetting schedule"
                        )
                    next_tick_time = time.time()

            except Exception as e:
                logger.error(f"Error in unified scheduler loop: {e}", exc_info=True)
                time.sleep(tick_interval_ms / 1000.0)

        logger.info("Unified scheduler loop exited")

    def _check_and_trigger_devices(self) -> None:
        """
        Check each device and trigger polling if conditions are met.

        For each device:
        1. Check if enough time has elapsed since last poll (per-device interval)
        2. Check device health (circuit breaker for dead/unknown devices)
           - If unhealthy (dead or unknown): skip polling, drain queue if backlog > 5 requests
           - Degraded devices continue to poll (they may recover)
        3. Check queue depth to prevent oversubscription
        4. Enqueue LOW priority poll request if all conditions are met

        Circuit breaker check MUST come before queue depth to prevent log spam
        when a dead device has accumulated a queue backlog.

        Queue draining prevents timeout requests from overwhelming the system when
        a USB-powered device is turned OFF but maintains UART connection.

        Skips polling and logs info/warning if device is unhealthy or queue is too deep.
        """
        now = time.time()

        # Get snapshot of devices to avoid holding lock during queue operations
        with self._lock:
            devices_snapshot = [
                (device_id, queue, self.device_intervals.get(device_id, self.default_interval_ms),
                 self.last_poll_time.get(device_id, 0.0))
                for device_id, queue in self.device_queues.items()
            ]

        for device_id, queue, interval_ms, last_poll in devices_snapshot:
            try:
                # Check 1: Has enough time elapsed?
                time_since_last_poll_ms = (now - last_poll) * 1000.0
                if time_since_last_poll_ms < interval_ms:
                    continue  # Not time yet

                # Check 2: Circuit breaker - is device unhealthy?
                # This check MUST come before queue depth to avoid log spam
                conn = self.device_connections.get(device_id)
                if conn and not conn.is_healthy():
                    # Device is dead or unknown - skip polling to avoid queue overflow
                    # Note: degraded devices (is_healthy=True) continue to poll
                    with self._lock:
                        self.skipped_polls[device_id] = self.skipped_polls.get(device_id, 0) + 1
                        skip_count = self.skipped_polls[device_id]

                        # Check if device just became unhealthy (health state transition)
                        was_healthy = self.device_was_healthy.get(device_id, True)
                        if was_healthy:
                            # Device transitioned from healthy to unhealthy - clear registry
                            self.device_was_healthy[device_id] = False
                            if self.registry:
                                self.registry.clear_disconnected(device_id)
                                logger.info(
                                    f"Device {device_id}: cleared registry due to health transition "
                                    f"(health: {conn.health_status}, failures: {conn.consecutive_failures})"
                                )

                    # Drain queue if it's building up while device is unhealthy
                    # This prevents timeout backlog from overwhelming the system
                    queue_depth = queue.qsize()
                    if queue_depth > 5:  # Only drain if queue has significant backlog
                        drained = 0
                        while queue.qsize() > 0:
                            req = queue.try_dequeue()
                            if req is None:
                                break
                            drained += 1
                        if drained > 0:
                            logger.info(
                                f"Device {device_id}: drained {drained} queued requests "
                                f"(health: {conn.health_status}, failures: {conn.consecutive_failures})"
                            )

                    # Log periodically based on health status
                    # Note: Only dead and unknown devices reach here (degraded devices continue to poll)
                    if skip_count % 20 == 1:
                        logger.info(
                            f"Device {device_id}: skipping poll due to {conn.health_status} health status "
                            f"(consecutive failures: {conn.consecutive_failures}). "
                            f"Total skipped: {skip_count}. "
                            f"Circuit breaker active - device will retry on reconnection."
                        )
                    continue

                # Device is healthy - update health tracking
                with self._lock:
                    was_healthy = self.device_was_healthy.get(device_id, True)
                    if not was_healthy:
                        # Device recovered - mark as healthy
                        self.device_was_healthy[device_id] = True
                        logger.info(f"Device {device_id}: recovered from unhealthy state")

                # Check 3: Is queue depth acceptable?
                queue_depth = queue.qsize()
                if queue_depth > self.max_queue_depth:
                    # Queue is too deep - skip this poll
                    with self._lock:
                        self.skipped_polls[device_id] = self.skipped_polls.get(device_id, 0) + 1
                        skip_count = self.skipped_polls[device_id]

                    # Log warning periodically (every 10 skips)
                    if skip_count % 10 == 1:
                        logger.warning(
                            f"Device {device_id}: skipping poll due to high queue depth "
                            f"({queue_depth} > {self.max_queue_depth}). "
                            f"Total skipped: {skip_count}. "
                            f"Device may be overloaded or polling interval too aggressive."
                        )
                    continue

                # All conditions met - enqueue poll request
                poll_request = PollRequest(
                    type="poll",
                    device_id=device_id,
                    now=now
                )
                queue.enqueue(poll_request, Priority.LOW)

                # Update last poll time
                with self._lock:
                    self.last_poll_time[device_id] = now

            except Exception as e:
                logger.error(
                    f"Failed to check/enqueue poll request for {device_id}: {e}",
                    exc_info=True
                )

    def get_interval_ms(self) -> float:
        """Get default polling interval in milliseconds."""
        return self.default_interval_ms

    def set_interval_ms(self, interval_ms: float) -> None:
        """
        Set new default polling interval.

        Note: This only affects the default. Per-device intervals are not changed.

        Args:
            interval_ms: New default interval in milliseconds (must be positive)

        Raises:
            ValueError: If interval_ms is not positive
        """
        if interval_ms <= 0:
            raise ValueError(f"Interval must be positive, got {interval_ms}")

        self.default_interval_ms = interval_ms
        logger.info(f"Unified scheduler default interval changed to {interval_ms}ms")

    def set_device_interval_ms(self, device_id: str, interval_ms: float) -> None:
        """
        Set polling interval for a specific device.

        Args:
            device_id: Device identifier
            interval_ms: New interval in milliseconds (must be positive)

        Raises:
            ValueError: If interval_ms is not positive or device not found
        """
        if interval_ms <= 0:
            raise ValueError(f"Interval must be positive, got {interval_ms}")

        with self._lock:
            if device_id not in self.device_queues:
                raise ValueError(f"Device {device_id} not registered")

            self.device_intervals[device_id] = interval_ms
            logger.info(f"Device {device_id}: polling interval changed to {interval_ms}ms")

    def get_stats(self) -> Dict:
        """
        Get scheduler statistics.

        Returns:
            Dictionary with scheduler stats (intervals, device count, queue depths, skipped polls)
        """
        with self._lock:
            device_stats = {}
            for device_id in self.device_queues.keys():
                queue = self.device_queues[device_id]
                device_stats[device_id] = {
                    "interval_ms": self.device_intervals.get(device_id, self.default_interval_ms),
                    "queue_depth": queue.qsize(),
                    "skipped_polls": self.skipped_polls.get(device_id, 0),
                    "last_poll_ago_ms": (time.time() - self.last_poll_time.get(device_id, 0.0)) * 1000.0
                }

            return {
                "running": self.running,
                "default_interval_ms": self.default_interval_ms,
                "max_queue_depth": self.max_queue_depth,
                "device_count": len(self.device_queues),
                "devices": device_stats,
            }
