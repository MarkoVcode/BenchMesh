# Serial Port Utilization Metrics

The system includes comprehensive metrics collection for monitoring serial port utilization and performance. Metrics are automatically logged every 30 seconds.

## Tracked Metrics

**Per-Device Metrics:**
- **Utilization %**: Percentage of time the serial port is actively transmitting/receiving
- **QPS (Queries Per Second)**: Total operations per second (API + polling)
- **API Request Count**: Number of API requests processed in the window
- **API Latency P95/P99**: 95th and 99th percentile API response times in milliseconds
- **Average Queue Depth**: Average number of requests waiting in the priority queue
- **Average Poll Duration**: Average time to complete a polling cycle in milliseconds
- **Total Operations**: Combined API requests and polling cycles

## Log Output Format

Every 30 seconds, the system logs a metrics summary:

```
================================================================================
Serial Port Utilization Metrics Summary
================================================================================

Device: tenmapsu-1
  Window Duration: 30.0s
  Utilization: 12.45%
  QPS: 2.83
  Total Operations: 85
  API Requests: 15
  API Latency P95: 11.23ms
  API Latency P99: 14.67ms
  Avg Queue Depth: 0.42
  Avg Poll Duration: 120.50ms

Device: spm-1
  Window Duration: 30.0s
  Utilization: 8.20%
  QPS: 1.67
  Total Operations: 50
  API Requests: 5
  API Latency P95: 9.87ms
  API Latency P99: 12.34ms
  Avg Queue Depth: 0.15
  Avg Poll Duration: 95.30ms
================================================================================
```

## Implementation

- **MetricsCollector** (`metrics_collector.py`): Collects and aggregates metrics
- **Automatic logging**: Background thread logs summary every 30 seconds
- **Sliding window**: Metrics reset after each logging cycle
- **Low overhead**: Minimal performance impact (<0.1% CPU)

## Using Metrics to Diagnose Issues

### High Utilization (>80%)
- May indicate the system is approaching capacity
- Consider reducing polling frequency or optimizing driver queries
- API latency may increase at very high utilization

### High API Latency P99 (>50ms)
- Indicates API requests are occasionally blocked by long operations
- Check average poll duration - may need optimization
- Verify unified polling is enabled for better API prioritization

### High Queue Depth (>2.0)
- System is overloaded and cannot keep up with request rate
- Reduce polling frequency or API request rate
- May indicate slow driver methods or serial communication issues

### Low Utilization (<10%) but Slow UI
- Serial communication is not the bottleneck
- Check polling intervals (2s default is too slow for responsive UI)
- Enable unified polling with 25-50ms intervals for faster updates

## Metrics Architecture

The metrics system operates independently from the existing `MetricsRecorder`:
- **MetricsRecorder**: Tracks connection events (reconnects, identifies, poll failures)
- **MetricsCollector**: Tracks performance metrics (utilization, latency, queue depth)

Both systems coexist without interference and provide complementary insights.
