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

    def __init__(self, interval_ms: float = 50.0, max_queue_depth: int = 10, device_connections: Optional[Dict[str, 'DeviceConnection']] = None, registry=None, metrics_collector=None):
        """
        Initialize unified scheduler.

        Args:
            interval_ms: Default polling interval in milliseconds (default 50ms = 20Hz)
            max_queue_depth: Maximum queue depth before throttling (default 10)
            device_connections: Map of device_id -> DeviceConnection for health checks
            registry: DeviceRegistry instance for clearing disconnected devices
            metrics_collector: Phase 4: MetricsCollector for recording throttling events
        """
        self.default_interval_ms = interval_ms
        self.max_queue_depth = max_queue_depth
        self.device_queues: Dict[str, DeviceRequestQueue] = {}
        self.device_connections: Dict[str, 'DeviceConnection'] = device_connections if device_connections is not None else {}
        self.device_intervals: Dict[str, float] = {}
        self.last_poll_time: Dict[str, float] = {}
        self.skipped_polls: Dict[str, int] = {}
        self.registry = registry
        self.device_was_healthy: Dict[str, bool] = {}  # Track previous health state
        self.metrics_collector = metrics_collector  # Phase 4: Metrics collection
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Adaptive throttling state (Phase 1)
        from .settings import settings
        self.settings = settings
        self.adaptive_throttling = settings.adaptive_throttling_enabled
        self.queue_throttle_start = settings.queue_throttle_start
        self.queue_throttle_tiers = settings.queue_throttle_tiers
        self.backoff_multiplier = settings.backoff_multiplier
        self.backoff_max_multiplier = settings.backoff_max_multiplier
        self.recovery_interval_ms = settings.recovery_interval_ms

        # Per-device backoff multipliers (exponential backoff on failures)
        self.backoff_multipliers: Dict[str, float] = {}

        # Per-device last recovery attempt time (for dead device retry)
        self.last_recovery_attempt: Dict[str, float] = {}

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

    def _calculate_throttle_probability(self, queue_depth: int, device_id: str) -> float:
        """
        Calculate probability of skipping a poll based on queue depth.

        Uses gradual tiered throttling instead of all-or-nothing:
        - 0-30% full: 0% skip (poll at 100% rate)
        - 30-60% full: 25% skip (poll at 75% rate)
        - 60-80% full: 50% skip (poll at 50% rate)
        - 80-100% full: 75% skip (poll at 25% rate)
        - >100% overflow: 100% skip (stop polling)

        Phase 2: Uses transport-specific max queue depth for accurate throttling.

        Args:
            queue_depth: Current queue depth
            device_id: Device identifier (for transport-specific limits)

        Returns:
            Probability of skipping (0.0-1.0)
        """
        # Phase 2: Get transport-specific max queue depth
        max_depth = self._get_transport_max_queue_depth(device_id)

        if not self.adaptive_throttling:
            # Legacy behavior: all-or-nothing at max_queue_depth
            return 1.0 if queue_depth > max_depth else 0.0

        # Calculate queue fullness percentage
        queue_fullness = queue_depth / max_depth

        if queue_fullness <= self.queue_throttle_start:
            # Not yet throttling
            return 0.0
        elif queue_fullness >= 1.0:
            # Overflow - stop completely
            return 1.0
        else:
            # Gradual throttling based on tiers
            # Map fullness range (throttle_start to 1.0) to throttle range (0.0 to 1.0)
            normalized_fullness = (queue_fullness - self.queue_throttle_start) / (1.0 - self.queue_throttle_start)

            # Tiered throttling (step function)
            tier_size = 1.0 / self.queue_throttle_tiers
            current_tier = int(normalized_fullness / tier_size)

            # Each tier increases skip probability
            skip_probability = (current_tier + 1) * tier_size

            return min(1.0, skip_probability)
    
    def _get_backoff_multiplier(self, device_id: str) -> float:
        """
        Get current backoff multiplier for device.
        
        Returns:
            Backoff multiplier (1.0 - backoff_max_multiplier)
        """
        return self.backoff_multipliers.get(device_id, 1.0)
    
    def _increase_backoff(self, device_id: str) -> None:
        """
        Increase backoff multiplier for device (exponential backoff).

        Args:
            device_id: Device identifier
        """
        current = self._get_backoff_multiplier(device_id)
        new_multiplier = min(current * self.backoff_multiplier, self.backoff_max_multiplier)
        self.backoff_multipliers[device_id] = new_multiplier

        # Phase 4: Record backoff change in metrics
        if self.metrics_collector:
            self.metrics_collector.update_backoff_multiplier(device_id, new_multiplier)

        logger.debug(
            f"Device {device_id}: increased backoff multiplier {current:.1f}x -> {new_multiplier:.1f}x"
        )
    
    def _reset_backoff(self, device_id: str) -> None:
        """
        Reset backoff multiplier for device (on success).

        Args:
            device_id: Device identifier
        """
        if device_id in self.backoff_multipliers:
            old_multiplier = self.backoff_multipliers[device_id]
            self.backoff_multipliers[device_id] = 1.0

            # Phase 4: Record backoff reset in metrics
            if self.metrics_collector:
                self.metrics_collector.update_backoff_multiplier(device_id, 1.0)

            logger.debug(
                f"Device {device_id}: reset backoff multiplier {old_multiplier:.1f}x -> 1.0x"
            )

    def _get_transport_max_queue_depth(self, device_id: str) -> int:
        """
        Get transport-specific max queue depth for device.

        Phase 2: Different transports have different buffer capacities:
        - USB TMC: 5 (more fragile, smaller buffers)
        - Serial: 10 (standard)
        - TCP/IP: 15 (network buffering)

        Args:
            device_id: Device identifier

        Returns:
            Transport-specific max queue depth
        """
        # Get transport type from device connection
        conn = self.device_connections.get(device_id)
        if not conn:
            return self.max_queue_depth  # Fallback to default

        transport_type = getattr(conn, 'transport_type', 'serial')

        # Return transport-specific limit
        if transport_type == 'usbtmc':
            return self.settings.usbtmc_max_queue_depth
        elif transport_type == 'tcpip':
            return self.settings.tcpip_max_queue_depth
        else:  # serial or unknown
            return self.settings.serial_max_queue_depth

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
                # Check 1: Has enough time elapsed? (with exponential backoff)
                # Apply backoff multiplier and quality-based speed adjustment
                backoff_mult = self._get_backoff_multiplier(device_id)
                
                # Get quality multiplier if available
                quality_mult = 1.0
                conn = self.device_connections.get(device_id)
                if conn and self.adaptive_throttling:
                    quality_mult = conn.get_quality_multiplier()
                
                # Calculate effective interval with all multipliers
                effective_interval_ms = interval_ms * backoff_mult * quality_mult
                
                time_since_last_poll_ms = (now - last_poll) * 1000.0
                if time_since_last_poll_ms < effective_interval_ms:
                    continue  # Not time yet

                # Check 2: Circuit breaker - is device unhealthy?
                # This check MUST come before queue depth to avoid log spam
                conn = self.device_connections.get(device_id)

                # Safety check: If no connection object exists, skip polling
                # This can happen during initialization or device removal
                if conn is None:
                    # No connection tracking - skip this device entirely
                    with self._lock:
                        self.skipped_polls[device_id] = self.skipped_polls.get(device_id, 0) + 1
                        skip_count = self.skipped_polls[device_id]

                    # Log occasionally (not every iteration to avoid spam)
                    if skip_count % 100 == 1:
                        logger.warning(
                            f"Device {device_id}: No connection object in scheduler. "
                            f"Device may not be fully initialized. Skipped {skip_count} polls."
                        )
                    continue

                # Circuit breaker: Only block confirmed "dead" devices
                # Allow "unknown" devices to poll so they can be tested and transition to healthy/dead
                # Allow "degraded" and "healthy" devices to continue polling
                if conn.health_status == "dead":
                    # Check if it's time for a recovery attempt
                    current_time = time.time() * 1000  # Convert to milliseconds
                    last_attempt = self.last_recovery_attempt.get(device_id, 0)
                    time_since_last_attempt = current_time - last_attempt

                    if time_since_last_attempt >= self.recovery_interval_ms:
                        # Time for recovery attempt - allow this poll to go through
                        self.last_recovery_attempt[device_id] = current_time
                        logger.info(
                            f"Device {device_id}: Attempting recovery poll after "
                            f"{time_since_last_attempt/1000:.1f}s (dead device with "
                            f"{conn.consecutive_failures} consecutive failures)"
                        )
                        # Don't skip - let the poll attempt run
                    else:
                        # Not time for recovery yet - skip polling to avoid queue overflow

                        # Phase 4: Update quality metrics for unhealthy device
                        self._update_quality_metrics(device_id)

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

                        # Log periodically for dead devices (every 200 skips to reduce spam)
                        if skip_count % 200 == 1:
                            logger.warning(
                                f"Device {device_id}: Circuit breaker active (dead device with "
                                f"{conn.consecutive_failures} consecutive failures). "
                                f"Total skipped: {skip_count}. Will retry after recovery interval."
                            )
                        continue

                # Device is healthy - update health tracking
                with self._lock:
                    was_healthy = self.device_was_healthy.get(device_id, True)
                    if not was_healthy:
                        # Device recovered - mark as healthy
                        self.device_was_healthy[device_id] = True
                        logger.info(f"Device {device_id}: recovered from unhealthy state")

                # Phase 4: Update quality metrics for all healthy/degraded/unknown devices
                self._update_quality_metrics(device_id)

                # Check 3: Gradual queue depth throttling
                queue_depth = queue.qsize()

                # Calculate throttle probability based on queue depth (Phase 2: transport-specific)
                throttle_probability = self._calculate_throttle_probability(queue_depth, device_id)

                # Decide whether to skip this poll based on probability
                import random
                should_skip = random.random() < throttle_probability

                if should_skip:
                    # Throttled - skip this poll
                    with self._lock:
                        self.skipped_polls[device_id] = self.skipped_polls.get(device_id, 0) + 1
                        skip_count = self.skipped_polls[device_id]

                    # Phase 4: Record throttle event in metrics
                    if self.metrics_collector:
                        self.metrics_collector.record_throttle_event(device_id)

                    # Log warning periodically (frequency depends on severity)
                    log_frequency = 50 if throttle_probability < 0.5 else 20
                    if skip_count % log_frequency == 1:
                        queue_fullness_pct = (queue_depth / self.max_queue_depth) * 100
                        logger.warning(
                            f"Device {device_id}: gradual throttling active "
                            f"(queue {queue_depth}/{self.max_queue_depth} = {queue_fullness_pct:.0f}% full, "
                            f"skip probability: {throttle_probability*100:.0f}%). "
                            f"Total skipped: {skip_count}. "
                            f"Consider reducing polling frequency."
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

    def notify_poll_success(self, device_id: str) -> None:
        """
        Notify scheduler of successful poll (for adaptive throttling).

        Resets backoff multiplier on success.

        Args:
            device_id: Device identifier
        """
        if self.adaptive_throttling:
            self._reset_backoff(device_id)

        # Phase 4: Update quality metrics from connection monitor
        self._update_quality_metrics(device_id)

    def notify_poll_failure(self, device_id: str) -> None:
        """
        Notify scheduler of failed poll (for adaptive throttling).

        Increases backoff multiplier on failure.

        Args:
            device_id: Device identifier
        """
        if self.adaptive_throttling:
            self._increase_backoff(device_id)

        # Phase 4: Update quality metrics from connection monitor
        self._update_quality_metrics(device_id)

    def _update_quality_metrics(self, device_id: str) -> None:
        """
        Phase 4: Update quality metrics in metrics collector from connection monitor.

        Args:
            device_id: Device identifier
        """
        if not self.metrics_collector:
            logger.debug(f"Device {device_id}: No metrics collector available")
            return

        conn = self.device_connections.get(device_id)
        if not conn:
            logger.debug(f"Device {device_id}: No connection object found")
            return

        # Get quality data from connection monitor if available and has sufficient data
        # BUT: Always override with health status for dead devices (circuit breaker frozen window issue)
        health = conn.health_status

        if health == "dead":
            # Dead devices ALWAYS show critical quality, regardless of rolling window
            # This prevents frozen scores when circuit breaker stops polling
            score, tier, trend = 0.0, "critical", "degrading"
        elif conn.quality_monitor and conn.quality_monitor.has_sufficient_data():
            # Quality monitor has enough samples - use calculated scores
            score = conn.quality_monitor.get_quality_score()
            tier = conn.quality_monitor.get_quality_tier()
            trend = conn.quality_monitor.get_quality_trend()
        else:
            # No quality monitor OR insufficient data - derive from health status
            if health == "healthy":
                score, tier, trend = 95.0, "excellent", "stable"
            elif health == "degraded":
                score, tier, trend = 50.0, "fair", "degrading"
            else:  # unknown
                score, tier, trend = 50.0, "fair", "stable"

        # Update metrics
        self.metrics_collector.update_quality_metrics(device_id, score, tier, trend)

        # Also update transport type
        transport_type = getattr(conn, 'transport_type', 'serial')
        self.metrics_collector.update_transport_type(device_id, transport_type)
