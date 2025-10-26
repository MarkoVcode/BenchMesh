from __future__ import annotations
from typing import Dict, Optional, Any, TYPE_CHECKING
import logging
import time
from .manifest_resolver import ManifestResolver
from .registry import DeviceRegistry
from .metrics import MetricsRecorder
from .metrics_collector import MetricsCollector
from .priority_queue import PriorityRequest, PollRequest, ApiRequest

if TYPE_CHECKING:
    from .connection import DeviceConnection

logger = logging.getLogger(__name__)

class DeviceWorker:
    """Run per-device polling cycles.

    Designed to be called periodically (or loop in a thread). For tests, run_once can be used.
    """
    def __init__(self, dev: dict, driver, registry: DeviceRegistry, resolver: ManifestResolver, metrics: MetricsRecorder | None = None, probe_map: Optional[Dict[str, float]] = None, interval_override: Optional[Dict[str, float]] = None, channels_override: Optional[Dict[str, int]] = None, metrics_collector: Optional[MetricsCollector] = None, connection: Optional['DeviceConnection'] = None, unified_scheduler=None):
        self.dev = dev
        self.driver = driver
        self.registry = registry
        self.resolver = resolver
        self.metrics = metrics
        self.metrics_collector = metrics_collector
        self.connection = connection
        self.unified_scheduler = unified_scheduler  # For adaptive throttling notifications
        self.last_probe_class: Dict[str, float] = probe_map if probe_map is not None else {}
        self.interval_override = interval_override
        self.channels_override = channels_override

    def run_once(self, now: float):
        dev_id = self.dev.get('id')
        if not dev_id:
            return
        # IDN gating
        if not (self.registry.data.get(dev_id) or {}).get('IDN'):
            return
        
        # Check if device uses unified multi-class polling
        if self.resolver.has_multi_class_polling(self.dev):
            self._run_multi_class_poll(now)
        else:
            self._run_per_class_poll(now)
    
    def _run_multi_class_poll(self, now: float):
        """
        Unified polling for multi-class devices.
        
        Calls a single poll method that returns data for all classes,
        avoiding multiple serial operations on a single port.
        """
        dev_id = self.dev.get('id')
        
        # Get device-level polling config
        poll_config = self.resolver.get_multi_class_poll_config(self.dev)
        if not poll_config:
            logger.warning(f"Device {dev_id} marked as multi-class but no poll config found")
            return
        
        meth_name = poll_config['method']
        poll_interval = poll_config['interval']
        
        # Check if it's time to poll (use 'unified' as the class key for timing)
        last_poll = self.last_probe_class.get('unified', 0.0)
        if now - last_poll < poll_interval:
            return
        
        # Get the poll method
        meth = getattr(self.driver, meth_name, None)
        if not callable(meth):
            logger.warning(f"Multi-class poll method {meth_name} not found on driver {type(self.driver).__name__}")
            return
        
        # Execute poll - should return dict keyed by class name
        class_channels = self.channels_override or self.resolver.get_classes_and_channels(self.dev)
        
        try:
            if self.metrics:
                self.metrics.inc_poll_total(dev_id, 'unified')

            # Poll channel 1 (multi-class devices typically have 1 channel)
            result = meth(1)

            if not result:
                if self.metrics:
                    self.metrics.inc_poll_failed(dev_id, 'unified')
                self.registry.clear_disconnected(dev_id)
                # Health: empty poll response = failure
                if self.connection:
                    self.connection.record_failure()

                # Notify scheduler of failure (for adaptive throttling)
                if self.unified_scheduler:
                    self.unified_scheduler.notify_poll_failure(dev_id)

                raise RuntimeError('poll_empty')

            # Distribute results by class
            for klass in class_channels.keys():
                class_data = result.get(klass)
                if class_data:
                    key = f"status_ch1"
                    self.registry.update(dev_id, key, class_data, klass=klass)

            # Health: successful poll
            if self.connection:
                self.connection.record_success()
            
            # Notify scheduler of success (for adaptive throttling)
            if self.unified_scheduler:
                self.unified_scheduler.notify_poll_success(dev_id)

            # Update last poll time
            self.last_probe_class['unified'] = now

        except RuntimeError as e:
            if str(e) == 'poll_empty':
                raise
            logger.error(f"Multi-class polling for {dev_id} failed: {e}")
            # Health: poll exception = failure
            if self.connection:
                self.connection.record_failure()
        except Exception as e:
            logger.warning(f"Multi-class polling for {dev_id} failed: {e}")
            if self.metrics:
                self.metrics.inc_poll_failed(dev_id, 'unified')
            # Health: poll exception = failure
            if self.connection:
                self.connection.record_failure()
            
            # Notify scheduler of failure (for adaptive throttling)
            if self.unified_scheduler:
                self.unified_scheduler.notify_poll_failure(dev_id)
    
    def _run_per_class_poll(self, now: float):
        """
        Legacy per-class polling for devices with separate class polling.
        
        Each class is polled independently with its own interval.
        """
        dev_id = self.dev.get('id')
        class_channels = self.channels_override or self.resolver.get_classes_and_channels(self.dev)
        poll_intervals = self.interval_override or self.resolver.get_poll_intervals(self.dev)
        
        for klass, ch_count in (class_channels or {}).items():
            poll_iv = poll_intervals.get(klass, 2.0)
            last_poll = self.last_probe_class.get(klass, 0.0)
            if now - last_poll < poll_iv:
                continue
            polled_any = False
            meth_name = self.resolver.get_poll_method(self.dev, klass) or 'poll_status'
            meth = getattr(self.driver, meth_name, None)
            if not callable(meth):
                logger.warning("Poll method %s not implemented on driver %s; skipping class %s", meth_name, type(self.driver).__name__, klass)
                continue
            for ch in range(1, max(1, ch_count)+1):
                if self.metrics:
                    self.metrics.inc_poll_total(dev_id, klass)
                try:
                    st = meth(ch)
                except Exception as e:
                    logger.warning("Polling %s[%s] failed: %s", dev_id, klass, e)
                    st = {}
                    # Health: poll exception = failure
                    if self.connection:
                        self.connection.record_failure()
                    
                    # Notify scheduler of failure (for adaptive throttling)
                    if self.unified_scheduler:
                        self.unified_scheduler.notify_poll_failure(dev_id)
                if not st:
                    if self.metrics:
                        self.metrics.inc_poll_failed(dev_id, klass)
                    # On empty/error poll, clear IDN and per-class status and drop connection by caller
                    self.registry.clear_disconnected(dev_id)
                    polled_any = False
                    # Health: empty poll response = failure
                    if self.connection:
                        self.connection.record_failure()

                    # Notify scheduler of failure (for adaptive throttling)
                    if self.unified_scheduler:
                        self.unified_scheduler.notify_poll_failure(dev_id)
                        
                    # signal caller to drop connection by raising a sentinel exception
                    raise RuntimeError('poll_empty')
                key = f"status_ch{ch}"
                self.registry.update(dev_id, key, st, klass=klass)
                polled_any = True
            if polled_any:
                self.last_probe_class[klass] = now
                # Health: successful poll
                if self.connection:
                    self.connection.record_success()
                
                # Notify scheduler of success (for adaptive throttling)
                if self.unified_scheduler:
                    self.unified_scheduler.notify_poll_success(dev_id)

    def process_request(self, priority_request: PriorityRequest) -> Any:
        """
        Process a request from the priority queue.

        Handles both polling requests (LOW priority) and API requests (HIGH priority).

        Args:
            priority_request: The request to process

        Returns:
            Result of the operation (for API requests)

        Raises:
            RuntimeError: If polling fails with 'poll_empty' sentinel
            Exception: Other errors during request processing
        """
        request = priority_request.request

        if isinstance(request, PollRequest):
            # Process polling request
            return self._process_poll_request(request)
        elif isinstance(request, ApiRequest):
            # Process API request
            return self._process_api_request(request)
        else:
            logger.warning(f"Unknown request type: {type(request)}")
            return None

    def _process_poll_request(self, request: PollRequest) -> None:
        """
        Process a polling request.

        Delegates to run_once for actual polling logic.

        Args:
            request: The poll request to process

        Raises:
            RuntimeError: If polling fails with 'poll_empty' sentinel
        """
        dev_id = self.dev.get('id')
        
        # Record serial operation start
        if self.metrics_collector and dev_id:
            self.metrics_collector.record_serial_operation_start(dev_id, 'poll')
        
        try:
            self.run_once(request.now)
            
            # Record operation end
            if self.metrics_collector and dev_id:
                self.metrics_collector.record_serial_operation_end(dev_id)
        except Exception as e:
            # Record operation end even on error
            if self.metrics_collector and dev_id:
                self.metrics_collector.record_serial_operation_end(dev_id)
            raise

    def _process_api_request(self, request: ApiRequest) -> Any:
        """
        Process an API request.

        Calls the specified driver method with provided arguments.

        Args:
            request: The API request to process

        Returns:
            Result of the driver method call

        Raises:
            AttributeError: If method doesn't exist on driver
            Exception: Any exception raised by the driver method
        """
        dev_id = self.dev.get('id')

        # Record serial operation start
        if self.metrics_collector and dev_id:
            self.metrics_collector.record_serial_operation_start(dev_id, 'api')
        
        start_time = time.time()

        try:
            # Get the method from driver
            method = getattr(self.driver, request.method)

            # Call with args and kwargs
            result = method(*request.args, **request.kwargs)

            logger.debug(f"API request for {dev_id}: {request.method}(*{request.args}, **{request.kwargs}) -> {result}")

            # Record metrics
            latency_ms = (time.time() - start_time) * 1000.0
            if self.metrics_collector and dev_id:
                self.metrics_collector.record_api_request(dev_id, request.method, latency_ms)
                self.metrics_collector.record_serial_operation_end(dev_id)

            return result

        except Exception as e:
            # Record operation end even on error
            if self.metrics_collector and dev_id:
                self.metrics_collector.record_serial_operation_end(dev_id)
            
            logger.error(f"API request failed for {dev_id}.{request.method}: {e}", exc_info=True)
            raise
