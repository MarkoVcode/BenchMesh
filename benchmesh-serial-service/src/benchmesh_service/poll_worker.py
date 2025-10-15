from __future__ import annotations
from typing import Dict, Optional, Any
import logging
import time
from .manifest_resolver import ManifestResolver
from .registry import DeviceRegistry
from .metrics import MetricsRecorder
from .metrics_collector import MetricsCollector
from .priority_queue import PriorityRequest, PollRequest, ApiRequest

logger = logging.getLogger(__name__)

class DeviceWorker:
    """Run per-device polling cycles.

    Designed to be called periodically (or loop in a thread). For tests, run_once can be used.
    """
    def __init__(self, dev: dict, driver, registry: DeviceRegistry, resolver: ManifestResolver, metrics: MetricsRecorder | None = None, probe_map: Optional[Dict[str, float]] = None, interval_override: Optional[Dict[str, float]] = None, channels_override: Optional[Dict[str, int]] = None, metrics_collector: Optional[MetricsCollector] = None):
        self.dev = dev
        self.driver = driver
        self.registry = registry
        self.resolver = resolver
        self.metrics = metrics
        self.metrics_collector = metrics_collector
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
                if not st:
                    if self.metrics:
                        self.metrics.inc_poll_failed(dev_id, klass)
                    # On empty/error poll, clear IDN and per-class status and drop connection by caller
                    self.registry.clear_disconnected(dev_id)
                    polled_any = False
                    # signal caller to drop connection by raising a sentinel exception
                    raise RuntimeError('poll_empty')
                key = f"status_ch{ch}"
                self.registry.update(dev_id, key, st, klass=klass)
                polled_any = True
            if polled_any:
                self.last_probe_class[klass] = now

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
