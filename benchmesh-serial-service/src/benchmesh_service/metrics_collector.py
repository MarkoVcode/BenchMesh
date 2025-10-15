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
    
    # Timing window
    window_start_time: float = field(default_factory=time.time)
    
    def reset_window(self):
        """Reset metrics for a new time window."""
        self.total_operation_time_ms = 0.0
        self.operation_count = 0
        self.api_request_count = 0
        self.window_start_time = time.time()
        # Keep latency/queue samples across windows for percentile calculations


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
            "total_operations": metrics.operation_count
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
            logger.info(f"\nDevice: {device_id}")
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
        
        logger.info("=" * 80)
