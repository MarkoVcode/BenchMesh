# Unified Polling & Priority Queue - Quick Reference

**Status**: Implemented (disabled by default for backward compatibility)

> **Related Documentation**: See `ai_context/UNIFIED_POLLING_DESIGN.md` for complete architecture and implementation details.

## Overview

The system supports unified polling with priority queues for improved performance and responsiveness.

## Architecture

- **UnifiedScheduler** (`unified_scheduler.py`): Central coordinator that triggers all devices simultaneously at a configurable interval
- **DeviceRequestQueue** (`priority_queue.py`): Per-device priority queue with HIGH priority for API requests, LOW priority for polling
- **Priority-based execution**: API requests jump to the front of the queue, ensuring <20ms response time even during active polling

## Benefits

- **Synchronized updates**: All devices poll at the same time → predictable UI updates
- **Fast API response**: API requests get HIGH priority and preempt background polling
- **Aggressive polling**: Can run at 25-50ms intervals (20-40 Hz) without blocking API
- **50-80x improvement**: UI update latency drops from 2000ms to 25-50ms

## Configuration

```bash
# Enable unified polling (disabled by default)
export BM_UNIFIED_POLLING=true

# Set polling interval in milliseconds (default: 50ms = 20 Hz)
export BM_UNIFIED_POLL_INTERVAL=50

# API request timeout for queued requests (default: 10s)
export BM_API_QUEUE_TIMEOUT=10.0
```

## Performance Characteristics

| Mode | Polling Interval | UI Staleness | API Latency | Device Utilization |
|------|------------------|--------------|-------------|-------------------|
| **Legacy** | 2000ms | Up to 2.0s | 10-26ms | <1% |
| **Unified (50ms)** | 50ms | Up to 50ms | 10-17ms | 35% |
| **Unified (25ms)** | 25ms | Up to 25ms | 10-17ms | 70% |

## Implementation Notes

- **Backward compatible**: Legacy mode (self-scheduled polling) remains default
- **Thread model unchanged**: Each device still has its own worker thread
- **Cross-device parallelism**: Multiple devices query simultaneously (different serial ports)
- **Priority queue**: API requests (HIGH) execute before polling (LOW)
- **Non-preemptive** (Phase 2): API waits for current operation to complete, then runs immediately

## Future: Phase 3 (Preemptive Scheduling)

Phase 3 would add preemptive interruption of multi-channel polls, allowing API requests to interrupt between channel queries. This enables 90%+ utilization while maintaining <17ms API latency. Not currently implemented.

## Testing

All 85 existing tests pass with unified polling disabled. To test unified polling:

```bash
# Run tests with unified polling enabled
BM_UNIFIED_POLLING=true pytest tests/

# Performance analysis
python3 scripts/performance_analysis.py
python3 scripts/unified_polling_analysis.py
```

## Design Documentation

- `ai_context/UNIFIED_POLLING_DESIGN.md`: Complete architecture and implementation details
- `scripts/performance_analysis.py`: Analyzes current system performance
- `scripts/unified_polling_analysis.py`: Models unified polling behavior and API blocking
