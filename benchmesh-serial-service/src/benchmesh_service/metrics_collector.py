from __future__ import annotations
import time
import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class DeviceMetrics:
    """Metrics for a single device over a time window."""
    device_id: str

    # Serial utilization tracking
    total_operation_time_ms: float = 0.0  # Cumulative time spent in serial I/O
    operation_count: int = 0

    # API request tracking
    api_latencies_ms: deque = field(default_factory=lambda: deque(maxlen=1000))  # Keep last 1000
    api_request_count: int = 0

    # Queue tracking
    queue_depth_samples: deque = field(default_factory=lambda: deque(maxlen=100))  # Last 100 samples

    # Poll duration tracking
    poll_durations_ms: deque = field(default_factory=lambda: deque(maxlen=100))

    # Phase 4: Adaptive throttling metrics
    throttle_events: int = 0  # Number of times poll was skipped due to throttling
    backoff_multiplier: float = 1.0  # Current backoff multiplier
    quality_score: float = 50.0  # Current connection quality score (0-100)
    quality_tier: str = "unknown"  # Current quality tier
    quality_trend: str = "stable"  # Current quality trend
    transport_type: str = "serial"  # Transport type (serial, usbtmc, tcpip)

    # Timing window
    window_start_time: float = field(default_factory=time.time)

    def reset_window(self):
        """Reset metrics for a new time window."""
        self.total_operation_time_ms = 0.0
        self.operation_count = 0
        self.api_request_count = 0
        self.throttle_events = 0  # Phase 4: Reset throttle events
        self.window_start_time = time.time()
        # Keep latency/queue samples and quality metrics across windows


@dataclass
class SerialOperation:
    """Tracks an in-progress serial operation."""
    device_id: str
    operation_type: str  # 'api' or 'poll'
    start_time: float


class MetricsCollector:
    """Collects serial port utilization and performance metrics."""
    
    def __init__(self, window_duration_s: float = 30.0):
        self.window_duration_s = window_duration_s
        self.device_metrics: Dict[str, DeviceMetrics] = {}
        self.active_operations: Dict[str, SerialOperation] = {}  # Key: device_id
        
    def _get_or_create_metrics(self, device_id: str) -> DeviceMetrics:
        """Get or create metrics object for a device."""
        if device_id not in self.device_metrics:
            self.device_metrics[device_id] = DeviceMetrics(device_id=device_id)
        return self.device_metrics[device_id]
    
    def record_serial_operation_start(self, device_id: str, operation_type: str):
        """Mark the start of a serial operation (api or poll)."""
        self.active_operations[device_id] = SerialOperation(
            device_id=device_id,
            operation_type=operation_type,
            start_time=time.time()
        )
    
    def record_serial_operation_end(self, device_id: str):
        """Mark the end of a serial operation and record duration."""
        op = self.active_operations.pop(device_id, None)
        if not op:
            return
        
        duration_ms = (time.time() - op.start_time) * 1000.0
        metrics = self._get_or_create_metrics(device_id)
        
        metrics.total_operation_time_ms += duration_ms
        metrics.operation_count += 1
        
        if op.operation_type == 'poll':
            metrics.poll_durations_ms.append(duration_ms)
    
    def record_api_request(self, device_id: str, method: str, latency_ms: float):
        """Record API request timing."""
        metrics = self._get_or_create_metrics(device_id)
        metrics.api_latencies_ms.append(latency_ms)
        metrics.api_request_count += 1
    
    def record_queue_depth(self, device_id: str, depth: int):
        """Record current queue depth."""
        metrics = self._get_or_create_metrics(device_id)
        metrics.queue_depth_samples.append(depth)

    def record_throttle_event(self, device_id: str):
        """Phase 4: Record a poll skip due to throttling."""
        metrics = self._get_or_create_metrics(device_id)
        metrics.throttle_events += 1

    def update_backoff_multiplier(self, device_id: str, multiplier: float):
        """Phase 4: Update current backoff multiplier."""
        metrics = self._get_or_create_metrics(device_id)
        metrics.backoff_multiplier = multiplier

    def update_quality_metrics(self, device_id: str, score: float, tier: str, trend: str):
        """Phase 4: Update connection quality metrics."""
        metrics = self._get_or_create_metrics(device_id)
        metrics.quality_score = score
        metrics.quality_tier = tier
        metrics.quality_trend = trend

    def update_transport_type(self, device_id: str, transport_type: str):
        """Phase 4: Update transport type for device."""
        metrics = self._get_or_create_metrics(device_id)
        metrics.transport_type = transport_type
    
    def get_device_metrics(self, device_id: str) -> Optional[Dict]:
        """Get current metrics for a specific device."""
        if device_id not in self.device_metrics:
            return None
        
        metrics = self.device_metrics[device_id]
        window_duration_s = time.time() - metrics.window_start_time
        
        # Calculate utilization %
        utilization_pct = 0.0
        if window_duration_s > 0:
            utilization_pct = (metrics.total_operation_time_ms / (window_duration_s * 1000.0)) * 100.0
            # Cap at 100% (can exceed if operations pile up in queue)
            utilization_pct = min(utilization_pct, 100.0)
        
        # Calculate API latency percentiles
        api_p95, api_p99 = None, None
        if metrics.api_latencies_ms:
            sorted_latencies = sorted(metrics.api_latencies_ms)
            n = len(sorted_latencies)
            api_p95 = sorted_latencies[int(n * 0.95)] if n > 0 else None
            api_p99 = sorted_latencies[int(n * 0.99)] if n > 0 else None
        
        # Calculate average queue depth
        avg_queue_depth = 0.0
        if metrics.queue_depth_samples:
            avg_queue_depth = sum(metrics.queue_depth_samples) / len(metrics.queue_depth_samples)
        
        # Calculate average poll duration
        avg_poll_duration_ms = 0.0
        if metrics.poll_durations_ms:
            avg_poll_duration_ms = sum(metrics.poll_durations_ms) / len(metrics.poll_durations_ms)
        
        # Calculate QPS (queries per second)
        qps = 0.0
        if window_duration_s > 0:
            qps = metrics.operation_count / window_duration_s
        
        # Phase 4: Calculate throttle rate
        throttle_rate_pct = 0.0
        if metrics.operation_count > 0:
            throttle_rate_pct = (metrics.throttle_events / (metrics.operation_count + metrics.throttle_events)) * 100.0

        return {
            "device_id": device_id,
            "window_duration_s": window_duration_s,
            "utilization_pct": utilization_pct,
            "qps": qps,
            "api_request_count": metrics.api_request_count,
            "api_latency_p95_ms": api_p95,
            "api_latency_p99_ms": api_p99,
            "avg_queue_depth": avg_queue_depth,
            "avg_poll_duration_ms": avg_poll_duration_ms,
            "total_operations": metrics.operation_count,
            # Phase 4: Adaptive throttling metrics
            "throttle_events": metrics.throttle_events,
            "throttle_rate_pct": throttle_rate_pct,
            "backoff_multiplier": metrics.backoff_multiplier,
            "quality_score": metrics.quality_score,
            "quality_tier": metrics.quality_tier,
            "quality_trend": metrics.quality_trend,
            "transport_type": metrics.transport_type
        }
    
    def get_utilization_summary(self) -> Dict[str, Dict]:
        """Get utilization summary for all devices."""
        summary = {}
        for device_id in self.device_metrics.keys():
            metrics = self.get_device_metrics(device_id)
            if metrics:
                summary[device_id] = metrics
        return summary
    
    def reset_window(self, device_id: Optional[str] = None):
        """Reset metrics window for a device or all devices."""
        if device_id:
            if device_id in self.device_metrics:
                self.device_metrics[device_id].reset_window()
        else:
            for metrics in self.device_metrics.values():
                metrics.reset_window()
    
    def log_summary(self):
        """Log a summary of all device metrics."""
        summary = self.get_utilization_summary()
        
        if not summary:
            logger.info("Serial Metrics: No data collected yet")
            return
        
        logger.info("=" * 80)
        logger.info("Serial Port Utilization Metrics Summary")
        logger.info("=" * 80)
        
        for device_id, metrics in summary.items():
            logger.info(f"\nDevice: {device_id} ({metrics['transport_type'].upper()})")
            logger.info(f"  Window Duration: {metrics['window_duration_s']:.1f}s")
            logger.info(f"  Utilization: {metrics['utilization_pct']:.2f}%")
            logger.info(f"  QPS: {metrics['qps']:.2f}")
            logger.info(f"  Total Operations: {metrics['total_operations']}")
            logger.info(f"  API Requests: {metrics['api_request_count']}")

            if metrics['api_latency_p95_ms'] is not None:
                logger.info(f"  API Latency P95: {metrics['api_latency_p95_ms']:.2f}ms")
            if metrics['api_latency_p99_ms'] is not None:
                logger.info(f"  API Latency P99: {metrics['api_latency_p99_ms']:.2f}ms")

            if metrics['avg_queue_depth'] > 0:
                logger.info(f"  Avg Queue Depth: {metrics['avg_queue_depth']:.2f}")

            if metrics['avg_poll_duration_ms'] > 0:
                logger.info(f"  Avg Poll Duration: {metrics['avg_poll_duration_ms']:.2f}ms")

            # Phase 4: Adaptive throttling metrics
            if metrics['throttle_events'] > 0:
                logger.info(f"  Throttle Events: {metrics['throttle_events']} ({metrics['throttle_rate_pct']:.1f}% skip rate)")

            if metrics['backoff_multiplier'] > 1.0:
                logger.info(f"  Backoff Multiplier: {metrics['backoff_multiplier']:.1f}x")

            logger.info(f"  Quality: {metrics['quality_tier']} (score: {metrics['quality_score']:.1f}, trend: {metrics['quality_trend']})")
        
        logger.info("=" * 80)
