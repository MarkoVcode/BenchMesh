import json
import os
import time
import threading
import logging
from typing import Dict, List, Any, Optional, Tuple
import yaml
from .logger import setup_logger
from .registry import DeviceRegistry
from .manifest_resolver import ManifestResolver
from .driver_factory import DriverFactory
from .clock import Clock
from .connection import DeviceConnection
from .poll_worker import DeviceWorker
from .reconnect import ReconnectPolicy
from .metrics import MetricsRecorder
from .metrics_collector import MetricsCollector
from .eol_detector import detect_eol_for_driver
from .priority_queue import DeviceRequestQueue, Priority, ApiRequest
from .unified_scheduler import UnifiedScheduler
from .settings import settings

logger = logging.getLogger(__name__)


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def _load_manifest(driver_key: str) -> Dict:
    # Prefer manifest colocated with driver package (new layout)
    pkg_dir = os.path.join(os.path.dirname(__file__), 'drivers', driver_key)
    pkg_manifest = os.path.join(pkg_dir, 'manifest.json')
    if os.path.exists(pkg_manifest):
        with open(pkg_manifest, 'r') as f:
            return json.load(f)

    # Fallback to repository-root drivers directory (legacy layout)
    here = _repo_root()
    legacy_manifest = os.path.join(here, 'drivers', driver_key, 'manifest.json')
    with open(legacy_manifest, 'r') as f:
        return json.load(f)







# Note: legacy dynamic driver loader removed. DriverFactory is the single source of truth.


class SerialManager:
    def __init__(self, config_source: Any, *, resolver: ManifestResolver | None = None, driver_factory: DriverFactory | None = None, clock: Clock | None = None, metrics: MetricsRecorder | None = None, policy: ReconnectPolicy | None = None):
        print("Initializing SerialManager with config:", config_source)
        self.logger = setup_logger()
        self.devices: List[Dict] = self._load_devices(config_source)
        self.keep_running = True
        self.dev_locks: Dict[str, threading.RLock] = {d.get('id'): threading.RLock() for d in self.devices if d.get('id')}
        self.dev_threads: Dict[str, threading.Thread] = {}
        self.registry_obj = DeviceRegistry({d.get('id'): {} for d in self.devices if d.get('id')})
        self.registry = self.registry_obj.data
        self.resolver = resolver or ManifestResolver()
        self.driver_factory = driver_factory or DriverFactory()
        self.clock = clock or Clock()
        self.metrics = metrics or MetricsRecorder()
        self.metrics_collector = MetricsCollector(window_duration_s=30.0)
        self.policy = policy or ReconnectPolicy()
        # External compatibility: connections map dev_id -> driver (or None)
        self.connections: Dict[str, object] = {}
        # Internal: device connections and workers
        self.dev_conns: Dict[str, DeviceConnection] = {}
        self.workers: Dict[str, DeviceWorker] = {}
        self._last_registry_log: float = 0.0
        # Backwards-compat attributes for tests
        self.last_open_attempt: Dict[str, float] = {}
        self.last_ok: Dict[str, float] = {}
        self.last_probe: Dict[str, float] = {}
        self.dev_class_channels: Dict[str, Dict[str, int]] = {}
        self.dev_class_poll_interval: Dict[str, Dict[str, float]] = {}
        self.last_probe_class: Dict[str, Dict[str, float]] = {}
        self.detected_eol: Dict[str, Tuple[str, str]] = {}  # Cache for auto-detected EOL settings
        self.initial_connect_tested: set = set()  # Track which devices have been tested on first connection

        # Unified polling and priority queue support
        self.unified_polling_enabled = settings.unified_polling_enabled
        self.device_queues: Dict[str, DeviceRequestQueue] = {}
        self.unified_scheduler: Optional[UnifiedScheduler] = None

        if self.unified_polling_enabled:
            # Create priority queues for each device
            for dev in self.devices:
                dev_id = dev.get('id')
                if dev_id:
                    self.device_queues[dev_id] = DeviceRequestQueue(dev_id)

            # Create unified scheduler with device connections for health checking
            self.unified_scheduler = UnifiedScheduler(
                interval_ms=settings.unified_poll_interval_ms,
                max_queue_depth=settings.max_queue_depth_threshold,
                device_connections=self.dev_conns,  # Pass reference to device connections
                registry=self.registry_obj,  # Pass registry for clearing disconnected devices
                metrics_collector=self.metrics_collector  # Phase 4: Pass metrics collector for throttling metrics
            )
            logger.info(
                f"Unified polling enabled: default_interval={settings.unified_poll_interval_ms}ms, "
                f"max_queue_depth={settings.max_queue_depth_threshold}, "
                f"devices={len(self.device_queues)}"
            )

        self.establish_connections()

    def _load_devices(self, source: Any) -> List[Dict]:
        if isinstance(source, list):
            return source
        # treat as path
        cfg_path = source if isinstance(source, str) else os.path.join(_repo_root(), 'config.yaml')
        if not os.path.isabs(cfg_path):
            cfg_path = os.path.join(_repo_root(), cfg_path)
        try:
            with open(cfg_path, 'r') as f:
                cfg = yaml.safe_load(f)
            return cfg.get('devices', []) if cfg else []
        except FileNotFoundError:
            # No config file - start with empty device list
            return []

    def establish_connections(self):
        print("Establishing connections to devices...")
        for device in self.devices:
            dev_id = device.get('id')
            if not dev_id:
                continue
            try:
                self._open_or_identify(device)
            except Exception as e:
                self.logger.info(f"Failed to connect to {device.get('name', dev_id)} on {device.get('port')}: {e}")


    def _get_eol_settings(self, dev: dict) -> Tuple[str, str]:
        """
        Get EOL settings for device, using cached detected settings if available.

        Returns:
            Tuple of (seol, reol)
        """
        dev_id = dev.get('id', 'unknown')

        # Check cache first
        if dev_id in self.detected_eol:
            return self.detected_eol[dev_id]

        # Otherwise use manifest settings
        return self.resolver.get_connection_eol(dev)

    def _try_detect_eol(self, dev: dict) -> bool:
        """
        Attempt to auto-detect correct EOL settings for a device.

        Only runs once per device. Stores result in cache for future connections.

        Returns:
            True if detection succeeded and settings were cached, False otherwise
        """
        dev_id = dev.get('id', 'unknown')

        # Skip if already detected
        if dev_id in self.detected_eol:
            return True

        driver_key = dev['driver']
        cls = self.driver_factory.load_driver_class(driver_key)
        manifest_seol, manifest_reol = self.resolver.get_connection_eol(dev)

        port = dev['port']
        baudrate = dev.get('baud', 115200)
        serial_mode = dev.get('serial', '8N1')

        logger.info(f"[{dev_id}] Starting EOL auto-detection...")

        detected = detect_eol_for_driver(
            cls,
            port,
            baudrate,
            serial_mode,
            manifest_seol,
            manifest_reol,
            dev_id
        )

        if detected:
            seol, reol = detected
            self.detected_eol[dev_id] = (seol, reol)
            logger.info(f"[{dev_id}] ✓ EOL auto-detection successful. Cached settings: seol={repr(seol)}, reol={repr(reol)}")
            return True
        else:
            logger.warning(f"[{dev_id}] ✗ EOL auto-detection failed. Will use manifest settings.")
            return False

    def _create_transport(self, dev: dict, seol: str, reol: str):
        """Create appropriate transport based on device config."""
        transport_type = dev.get('transport', 'serial')  # Default to serial for backward compat

        if transport_type == 'serial':
            from .transport import SerialTransport
            return SerialTransport(
                dev['port'],
                dev.get('baud', 115200),
                serial_mode=dev.get('serial', '8N1'),
                seol=seol,
                reol=reol,
            )
        elif transport_type == 'usbtmc':
            from .transport import UsbTmcTransport
            return UsbTmcTransport(
                device=dev['device'],
                seol=seol,
                reol=reol,
            )
        elif transport_type == 'tcpip':
            # Future: TCP/IP transport
            raise NotImplementedError(f"TCP/IP transport not yet implemented")
        else:
            raise ValueError(f"Unknown transport type: {transport_type}")

    def _make_driver(self, dev: dict):
        """Create driver instance using EOL settings (from cache or manifest)."""
        driver_key = dev['driver']
        cls = self.driver_factory.load_driver_class(driver_key)
        seol, reol = self._get_eol_settings(dev)

        # Validate transport is supported by driver
        transport_type = dev.get('transport', 'serial')
        manifest = self.resolver._load_manifest(driver_key)
        supported_transports = manifest.get('supported_transports', ['serial'])

        if transport_type not in supported_transports:
            raise ValueError(
                f"Device {dev.get('id')}: Transport '{transport_type}' not supported by driver '{driver_key}'. "
                f"Supported transports: {supported_transports}"
            )

        # Create and open transport
        transport = self._create_transport(dev, seol, reol).open()

        # Instantiate driver with transport
        return cls(transport=transport)

    def _open_or_identify(self, dev: dict):
        dev_id = dev.get('id')
        if not dev_id:
            return None
        conn = self.dev_conns.get(dev_id)
        if not conn:
            # Phase 2: Extract transport type for transport-specific limits
            transport_type = dev.get('transport', 'serial')  # Default to 'serial' if not specified

            conn = DeviceConnection(
                None,
                self.clock,
                failure_threshold=settings.health_failure_threshold,
                degraded_threshold=settings.health_degraded_threshold,
                enable_quality_monitoring=settings.adaptive_throttling_enabled,
                quality_window_size=settings.quality_window_size,
                quality_success_points=settings.quality_success_points,
                quality_timeout_penalty=settings.quality_timeout_penalty,
                quality_error_penalty=settings.quality_error_penalty,
                transport_type=transport_type
            )
            self.dev_conns[dev_id] = conn
            self.connections[dev_id] = None
        now = self.clock.now()
        # Attempt open/reconnect
        if not conn.is_open() and conn.can_attempt_open(self.policy.reconnect_interval):
            conn.mark_attempt()
            self.metrics.inc_reconnect_attempt(dev_id)
            try:
                drv = self._make_driver(dev)
                from .transport import SerialTransport
                if isinstance(drv, SerialTransport):
                    class _Adapter:
                        def __init__(self, t):
                            self.t = t
                        def close(self):
                            self.t.close()
                        def query_identify(self):
                            self.t.write_line('*IDN?')
                            return self.t.read_until_reol(1024)
                    drv = _Adapter(drv)

                conn.driver = drv
                self.connections[dev_id] = drv
                # If we had a worker, update its driver reference
                if dev_id in self.workers:
                    self.workers[dev_id].driver = drv
                self.metrics.inc_reconnect_success(dev_id)
                conn.reset_health()  # Health: new connection, reset health state
            except Exception as e:
                # If connection failed and we haven't tried EOL detection yet, try it once
                if dev_id not in self.initial_connect_tested:
                    self.initial_connect_tested.add(dev_id)
                    logger.debug(f"[{dev_id}] Initial connection failed: {e}. Attempting EOL auto-detection...")
                    if self._try_detect_eol(dev):
                        # Detection succeeded, try connecting again with detected settings
                        try:
                            drv = self._make_driver(dev)
                            from .transport import SerialTransport
                            if isinstance(drv, SerialTransport):
                                class _Adapter:
                                    def __init__(self, t):
                                        self.t = t
                                    def close(self):
                                        self.t.close()
                                    def query_identify(self):
                                        self.t.write_line('*IDN?')
                                        return self.t.read_until_reol(1024)
                                drv = _Adapter(drv)
                            conn.driver = drv
                            self.connections[dev_id] = drv
                            if dev_id in self.workers:
                                self.workers[dev_id].driver = drv
                            self.metrics.inc_reconnect_success(dev_id)
                            return conn.driver
                        except Exception as e2:
                            logger.error(f"[{dev_id}] Connection failed even after EOL detection: {e2}")

                # Connection failed
                conn.driver = None
                # Ensure registry reflects disconnected state
                self.registry_obj.clear_disconnected(dev_id)
                return None
        # Ensure a worker exists even if not identified yet; it will be IDN-gated
        if dev_id not in self.workers:
            probe_map = getattr(self, 'last_probe_class', {}).setdefault(dev_id, {})
            self.workers[dev_id] = DeviceWorker(dev, conn.driver, self.registry_obj, self.resolver, self.metrics, probe_map, metrics_collector=self.metrics_collector, connection=conn, unified_scheduler=self.unified_scheduler)
        # Identify-only cadence
        if conn.is_open() and (not self.registry.get(dev_id, {}).get('IDN')) and conn.can_attempt_open(self.policy.identify_interval):
            conn.mark_attempt()
            try:
                ident = conn.identify()
                # Always store IDN, even if empty, so registry shows {"IDN": ""} instead of {}
                self.registry_obj.set_idn(dev_id, ident or "")
                if ident:
                    self.metrics.inc_identify_success(dev_id)
                    conn.mark_ok()
                    conn.record_success()  # Health: successful identify
                else:
                    # Empty identify response - EOL settings might be incorrect or device powered off
                    self.metrics.inc_identify_fail(dev_id)
                    conn.record_failure()  # Health: empty response = failure
                    # Try auto-detection on first identify failure
                    if dev_id not in self.initial_connect_tested:
                        self.initial_connect_tested.add(dev_id)
                        logger.warning(f"[{dev_id}] Empty identify response - EOL settings may be incorrect. Attempting auto-detection...")
                        if self._try_detect_eol(dev):
                            # Close current driver and recreate with detected settings
                            try:
                                conn.driver.close()
                            except:
                                pass
                            drv = self._make_driver(dev)
                            from .transport import SerialTransport
                            if isinstance(drv, SerialTransport):
                                class _Adapter:
                                    def __init__(self, t):
                                        self.t = t
                                    def close(self):
                                        self.t.close()
                                    def query_identify(self):
                                        self.t.write_line('*IDN?')
                                        return self.t.read_until_reol(1024)
                                drv = _Adapter(drv)
                            conn.driver = drv
                            self.connections[dev_id] = drv
                            if dev_id in self.workers:
                                self.workers[dev_id].driver = drv
            except Exception as e:
                self.metrics.inc_identify_fail(dev_id)
                conn.record_failure()  # Health: exception = failure (timeout/communication error)
                # Communication exception during identify - try auto-detection
                if dev_id not in self.initial_connect_tested:
                    self.initial_connect_tested.add(dev_id)
                    logger.debug(f"[{dev_id}] Identify exception: {e}. Attempting auto-detection...")
                    if self._try_detect_eol(dev):
                        # Close current driver and recreate with detected settings
                        try:
                            conn.driver.close()
                        except:
                            pass
                        drv = self._make_driver(dev)
                        from .transport import SerialTransport
                        if isinstance(drv, SerialTransport):
                            class _Adapter:
                                def __init__(self, t):
                                    self.t = t
                                def close(self):
                                    self.t.close()
                                def query_identify(self):
                                    self.t.write_line('*IDN?')
                                    return self.t.read_until_reol(1024)
                            drv = _Adapter(drv)
                        conn.driver = drv
                        self.connections[dev_id] = drv
                        if dev_id in self.workers:
                            self.workers[dev_id].driver = drv
        return conn.driver



    def _update_registry(self, dev_id: str, key: str, value: Any, klass: str | None = None):
        self.registry_obj.update(dev_id, key, value, klass)

    def remove_registry_item(self, dev_id: str, key: str | None = None, prefix: bool = False, klass: str | None = None):
        self.registry_obj.remove_item(dev_id, key, prefix, klass)

    def clear_device_registry(self, dev_id: str):
        self.registry_obj.clear_device(dev_id)

    def _clear_disconnected_registry(self, dev_id: str):
        self.registry_obj.clear_disconnected(dev_id)

    # Removed legacy monitor and status helpers. Device threads handle cadence.

    def _device_worker(self, dev_id: str):
        """
        Device worker thread.

        In unified polling mode: Processes requests from priority queue
        In legacy mode: Self-schedules polling every 500ms
        """
        if self.unified_polling_enabled:
            self._device_worker_queue_mode(dev_id)
        else:
            self._device_worker_legacy_mode(dev_id)

    def _device_worker_queue_mode(self, dev_id: str):
        """
        Device worker in queue mode (unified polling enabled).

        Processes requests from the device's priority queue.
        HIGH priority: API requests
        LOW priority: Polling requests (from unified scheduler)
        """
        queue = self.device_queues.get(dev_id)
        if not queue:
            logger.error(f"No queue for device {dev_id} in unified polling mode")
            return

        logger.info(f"Device worker {dev_id} starting in queue mode")

        while self.keep_running:
            # Get next request from priority queue (blocking with timeout)
            priority_request = queue.dequeue(timeout=1.0)

            if priority_request is None:
                # Timeout - check if we should continue
                continue

            # Record queue depth for metrics
            if self.metrics_collector:
                current_depth = queue.qsize()
                self.metrics_collector.record_queue_depth(dev_id, current_depth)

            lock = self.dev_locks.get(dev_id)
            if not lock:
                logger.warning(f"No lock for device {dev_id}")
                continue

            with lock:
                queue.set_current_request(priority_request)

                try:
                    dev = next((d for d in self.devices if d.get('id') == dev_id), None)
                    if not dev:
                        continue

                    # Process the request (poll or API)
                    request = priority_request.request

                    if isinstance(request, ApiRequest):
                        # API REQUEST: Fast path - skip connection maintenance
                        # Connection check: fail fast if device not ready
                        if self.connections.get(dev_id) is None:
                            error = ConnectionError(f"Device {dev_id} not connected")
                            logger.warning(f"API request for {dev_id}.{request.method} rejected: device not connected")
                            if request.result_callback:
                                request.result_callback(error)
                            continue  # Skip to next request

                        # Device is connected - execute immediately
                        w = self.workers.get(dev_id)
                        if w:
                            # Inject test overrides if present
                            w.interval_override = self.dev_class_poll_interval.get(dev_id) or None
                            if dev_id in self.last_probe_class:
                                w.last_probe_class = self.last_probe_class[dev_id]

                            try:
                                result = w.process_request(priority_request)
                                if request.result_callback:
                                    request.result_callback(result)
                            except Exception as e:
                                logger.error(f"API request {dev_id}.{request.method} failed: {e}")
                                if request.result_callback:
                                    request.result_callback(e)
                    else:
                        # POLLING REQUEST: Normal path with connection maintenance
                        # Handle reconnection if needed
                        if self.connections.get(dev_id) is None:
                            last_attempt = self.last_open_attempt.get(dev_id, 0.0)
                            now = time.time()
                            if now - last_attempt >= 0.5:
                                self.last_open_attempt[dev_id] = now
                                try:
                                    self.reconnect(dev_id)
                                except Exception:
                                    pass
                        else:
                            # Normal path: ensure device is open and identified
                            self._open_or_identify(dev)

                        # Process polling request
                        w = self.workers.get(dev_id)
                        if w:
                            # Inject test overrides if present
                            w.interval_override = self.dev_class_poll_interval.get(dev_id) or None
                            if dev_id in self.last_probe_class:
                                w.last_probe_class = self.last_probe_class[dev_id]

                            try:
                                w.process_request(priority_request)
                            except RuntimeError as e:
                                if str(e) == 'poll_empty':
                                    # Drop connection
                                    self.connections[dev_id] = None
                                    if dev_id in self.dev_conns:
                                        self.dev_conns[dev_id].driver = None

                except Exception as e:
                    logger.error(f"Error processing request for {dev_id}: {e}", exc_info=True)
                finally:
                    queue.set_current_request(None)

            # Periodic registry logging
            if time.time() - self._last_registry_log >= 5.0:
                self._last_registry_log = time.time()
                try:
                    logger.debug("Registry snapshot: %s", json.dumps(self.registry, ensure_ascii=False))
                except Exception:
                    logger.debug("Registry snapshot (repr): %r", self.registry)

        logger.info(f"Device worker {dev_id} exiting (queue mode)")

    def _device_worker_legacy_mode(self, dev_id: str):
        """
        Device worker in legacy mode (unified polling disabled).

        Self-schedules polling every 500ms.
        """
        logger.info(f"Device worker {dev_id} starting in legacy mode")

        while self.keep_running:
            lock = self.dev_locks.get(dev_id)
            if not lock:
                time.sleep(0.5)
                continue
            with lock:
                now = time.time()
                dev = next((d for d in self.devices if d.get('id') == dev_id), None)
                if not dev:
                    time.sleep(0.5)
                    continue
                # Back-compat windowed reconnect attempt uses reconnect() for test spy
                if self.connections.get(dev_id) is None:
                    last_attempt = self.last_open_attempt.get(dev_id, 0.0)
                    if now - last_attempt >= 0.5:
                        self.last_open_attempt[dev_id] = now
                        try:
                            self.reconnect(dev_id)
                        except Exception:
                            pass
                else:
                    # Normal path: open/identify and then run worker
                    self._open_or_identify(dev)
                w = self.workers.get(dev_id)
                if w:
                    # Inject latest test overrides if present
                    w.interval_override = self.dev_class_poll_interval.get(dev_id) or None
                    if dev_id in self.last_probe_class:
                        w.last_probe_class = self.last_probe_class[dev_id]
                    try:
                        w.run_once(now)
                    except RuntimeError as e:
                        if str(e) == 'poll_empty':
                            # Drop connection and rely on reconnect cadence
                            self.connections[dev_id] = None
                            if dev_id in self.dev_conns:
                                self.dev_conns[dev_id].driver = None
                        else:
                            raise
            if time.time() - self._last_registry_log >= 5.0:
                self._last_registry_log = time.time()
                try:
                    logger.debug("Registry snapshot: %s", json.dumps(self.registry, ensure_ascii=False))
                except Exception:
                    logger.debug("Registry snapshot (repr): %r", self.registry)
            time.sleep(0.5)

        logger.info(f"Device worker {dev_id} exiting (legacy mode)")

    def reconnect(self, device_or_id):
        if isinstance(device_or_id, dict):
            dev = device_or_id
        else:
            dev = next((d for d in self.devices if d.get('id') == device_or_id), None)
        if not dev:
            return None
        return self._open_or_identify(dev)

    def enqueue_api_request(self, device_id: str, method: str, args: tuple = (), kwargs: dict = None) -> Any:
        """
        Enqueue a HIGH priority API request for a device.

        Used by the API layer to execute driver methods with priority over polling.

        Args:
            device_id: Device identifier
            method: Driver method name to call
            args: Positional arguments for method
            kwargs: Keyword arguments for method

        Returns:
            Result from the driver method

        Raises:
            ValueError: If device not found or unified polling not enabled
            TimeoutError: If request times out
            Exception: Any exception from driver method
        """
        if not self.unified_polling_enabled:
            raise ValueError("API request queueing requires unified polling to be enabled")

        queue = self.device_queues.get(device_id)
        if not queue:
            raise ValueError(f"Device {device_id} not found or has no queue")

        # Create a synchronization event for result
        import threading
        result_event = threading.Event()
        result_container = {'value': None, 'exception': None}

        def result_callback(result):
            """Callback invoked by worker with result or exception"""
            if isinstance(result, Exception):
                result_container['exception'] = result
            else:
                result_container['value'] = result
            result_event.set()

        # Create API request
        api_request = ApiRequest(
            type="api",
            device_id=device_id,
            method=method,
            args=args,
            kwargs=kwargs or {},
            result_callback=result_callback
        )

        # Enqueue with HIGH priority
        queue.enqueue(api_request, Priority.HIGH)
        logger.debug(f"Enqueued HIGH priority API request: {device_id}.{method}")

        # Wait for result (with timeout)
        timeout = settings.api_request_timeout_queue_s
        if not result_event.wait(timeout=timeout):
            raise TimeoutError(
                f"API request to {device_id}.{method} timed out after {timeout}s"
            )

        # Return result or raise exception
        if result_container['exception']:
            raise result_container['exception']

        return result_container['value']

    def start(self):
        self.establish_connections()
        # Start one worker thread per device for concurrent monitoring
        for dev in self.devices:
            dev_id = dev.get('id')
            if not dev_id:
                continue
            if dev_id in self.dev_threads and self.dev_threads[dev_id].is_alive():
                continue
            t = threading.Thread(target=self._device_worker, args=(dev_id,), name=f"dev-worker-{dev_id}", daemon=True)
            self.dev_threads[dev_id] = t
            t.start()

        # Start unified scheduler if enabled
        if self.unified_polling_enabled and self.unified_scheduler:
            # Register all device queues with scheduler (with device-specific intervals)
            for dev_id, queue in self.device_queues.items():
                # Find the device config
                dev = next((d for d in self.devices if d.get('id') == dev_id), None)
                if not dev:
                    continue

                # Check for device-level multi-class polling first
                interval_ms = None
                multi_class_config = self.resolver.get_multi_class_poll_config(dev)
                if multi_class_config:
                    # Multi-class device: use device-level interval
                    interval_ms = multi_class_config['interval'] * 1000.0
                else:
                    # Single-class device: use class-level intervals
                    poll_intervals = self.resolver.get_poll_intervals(dev)
                    if poll_intervals:
                        min_interval_s = min(poll_intervals.values())
                        interval_ms = min_interval_s * 1000.0

                # Register device with scheduler
                self.unified_scheduler.register_device(dev_id, queue, interval_ms=interval_ms)

            # Start the scheduler
            self.unified_scheduler.start()
            logger.info("Unified polling scheduler started")

        # Start metrics logging thread
        metrics_thread = threading.Thread(
            target=self._metrics_logger_loop,
            name="metrics-logger",
            daemon=True
        )
        metrics_thread.start()
        logger.info("Metrics logging thread started")
        # Keep legacy monitor if needed for any global duties (optional). Can be disabled if redundant.
        # threading.Thread(target=self.monitor_connections, daemon=True).start()

    def _metrics_logger_loop(self):
        """Background thread that logs metrics periodically."""
        while self.keep_running:
            # Sleep for 30 seconds
            for _ in range(30):
                if not self.keep_running:
                    break
                time.sleep(1.0)
            
            if self.keep_running and self.metrics_collector:
                # Log metrics summary
                self.metrics_collector.log_summary()
                # Reset metrics window for next period
                self.metrics_collector.reset_window()

    def stop(self):
        """Stop all device workers and close all serial connections"""
        self.logger.info("SerialManager shutting down...")

        # Stop unified scheduler first
        if self.unified_polling_enabled and self.unified_scheduler:
            self.unified_scheduler.stop()
            logger.info("Unified polling scheduler stopped")

        # Signal all workers to stop
        self.keep_running = False

        # Join worker threads with timeout
        for dev_id, t in list(self.dev_threads.items()):
            try:
                self.logger.info(f"Stopping worker thread for {dev_id}")
                t.join(timeout=2.0)
                if t.is_alive():
                    self.logger.warning(f"Worker thread {dev_id} did not stop cleanly")
                else:
                    self.logger.info(f"Worker thread {dev_id} stopped")
            except Exception as e:
                self.logger.error(f"Error stopping worker {dev_id}: {e}")

        # Close all serial connections
        for dev_id, drv in list(self.connections.items()):
            if drv is not None:
                try:
                    self.logger.info(f"Closing connection for {dev_id}")
                    drv.close()
                except Exception as e:
                    self.logger.error(f"Error closing connection {dev_id}: {e}")

        self.logger.info("SerialManager shutdown complete, all connections closed")

