# Circuit Breaker Implementation

## Overview

The unified scheduler includes a circuit breaker pattern that prevents log spam and queue overflow when devices become unresponsive. This is particularly important for USB-powered instruments that maintain UART connections even when powered OFF.

## Problem Solved

When a USB-powered instrument is switched OFF while maintaining its USB connection:
1. The serial port remains "open" but the instrument doesn't respond to queries
2. Each poll request times out after ~300ms
3. The scheduler enqueues new polls every 50ms (default interval)
4. Queue depth rapidly exceeds threshold (11+ requests)
5. Logs flood with "queue depth" warnings every 100ms

## Solution: Circuit Breaker with Queue Draining

### Health States

Devices transition through health states based on consecutive failures:

- **unknown**: Initial state, no polling until device is identified
- **healthy**: Device responding normally to queries (0 failures)
- **degraded**: Some failures detected, still attempting communication (1-2 failures)
- **dead**: Multiple consecutive failures, device unresponsive (3+ failures)

### Check Order (Critical!)

The scheduler checks conditions in this specific order:

1. **Timing**: Has enough time elapsed since last poll?
2. **Circuit Breaker**: Is device unhealthy (dead or unknown)?
3. **Queue Depth**: Is queue depth within threshold?

**The circuit breaker MUST be checked before queue depth** to prevent log spam when dead devices accumulate queue backlogs.

### Circuit Breaker Behavior

| Health Status | Polling Behavior | Registry Clearing | Logging |
|---------------|-----------------|-------------------|---------|
| healthy | Poll normally | No | None |
| degraded | **Continue polling** (may recover) | No | None |
| dead | Skip polling, drain queue if >5 backlog | **Yes (on transition)** | INFO every 20 skips |
| unknown | Skip polling, drain queue if >5 backlog | **Yes (on transition)** | INFO every 20 skips |

**Key Insights**:
- Degraded devices (1-2 failures) continue to be polled because they may recover. Only dead (3+ failures) and unknown devices trigger the circuit breaker.
- **Registry is cleared when device transitions from healthy to unhealthy**, removing IDN and status data. This causes the UI to show the device as offline.
- Registry clearing happens ONCE on the health state transition, not repeatedly.

### Queue Draining

When the circuit breaker detects an unhealthy device with queue depth > 5:
1. Drain all pending requests from the queue
2. Log the number of drained requests
3. Prevent timeout backlog from overwhelming the system

This prevents the scenario where a dead device accumulates hundreds of timeout requests in its queue.

## Configuration

Circuit breaker thresholds are configured in `settings.py`:

```python
# Health monitoring configuration
health_failure_threshold: int = 3     # Mark dead after N failures
health_degraded_threshold: int = 1    # Mark degraded after N failures
```

## Testing

Comprehensive tests in `tests/test_unified_scheduler.py` verify:

1. ✅ Dead devices are skipped by circuit breaker
2. ✅ Unknown devices are skipped by circuit breaker
3. ✅ Degraded devices continue to be polled
4. ✅ Healthy devices are polled normally
5. ✅ Queue draining when unhealthy device has backlog >5
6. ✅ No queue draining when backlog ≤5
7. ✅ Circuit breaker checked BEFORE queue depth
8. ✅ Queue depth warnings still work for healthy overloaded devices
9. ✅ Backward compatibility (no warnings without device_connections)
10. ✅ **Registry cleared when device transitions from healthy to unhealthy**
11. ✅ **Registry not cleared repeatedly (only on transition)**
12. ✅ **Device recovery detection and health tracking**

## Expected Log Behavior

### Before Circuit Breaker
```
WARNING - Device dmm-1: skipping poll due to high queue depth (11 > 10). Total skipped: 4781...
WARNING - Device dmm-1: skipping poll due to high queue depth (11 > 10). Total skipped: 4791...
WARNING - Device dmm-1: skipping poll due to high queue depth (11 > 10). Total skipped: 4801...
[Repeats every 100ms, thousands of warnings]
```

### After Circuit Breaker (with Registry Clearing)
```
INFO - Device dmm-1: cleared registry due to health transition (health: dead, failures: 5)
INFO - Device dmm-1: drained 8 queued requests (health: dead, failures: 5)
INFO - Device dmm-1: skipping poll due to dead health status (consecutive failures: 5). Total skipped: 1. Circuit breaker active...
INFO - Device dmm-1: skipping poll due to dead health status (consecutive failures: 5). Total skipped: 21. Circuit breaker active...
INFO - Device dmm-1: skipping poll due to dead health status (consecutive failures: 5). Total skipped: 41. Circuit breaker active...
[Logs only every 20 skips, INFO level instead of WARNING]
[UI shows device as offline due to registry being cleared]
```

## Code References

- Circuit breaker logic: `unified_scheduler.py:226-282`
- Registry clearing on health transition: `unified_scheduler.py:236-246`
- Health state machine: `connection.py:78-95`
- Queue draining: `unified_scheduler.py:248-262`
- Health tracking and recovery detection: `unified_scheduler.py:275-281`
- Settings: `settings.py:21-23`
- Tests: `tests/test_unified_scheduler.py` (12 tests, all passing)

## Future Improvements

- Consider making drain threshold configurable (currently hardcoded to 5)
- Add metrics for circuit breaker activations
- Implement recovery detection (log when device transitions from dead → healthy)
