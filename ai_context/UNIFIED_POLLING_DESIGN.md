# Unified Polling with Priority Queue - Implementation Design

## Executive Summary

This document outlines the design for implementing unified parallel polling with preemptive priority queuing to achieve:
- **25-50ms UI update latency** (down from 2000ms)
- **<20ms API response time** guaranteed worst-case
- **80-90% polling utilization** without blocking API requests
- **Synchronized device polling** for predictable UI updates

## Analysis Results

### Current State
- Per-device independent polling threads
- 2.0s polling interval → up to 2.8s UI staleness
- Simple lock-based synchronization
- API worst-case: 26ms (good, but can be blocked)

### Target State
- Unified polling scheduler (all devices poll simultaneously)
- 25-50ms polling interval → 25-50ms UI staleness (50x improvement!)
- Preemptive priority queue per device
- API worst-case: 17ms (guaranteed, never blocked)

## Architecture Design

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Unified Polling Scheduler                   │
│  (Central coordinator, triggers all devices at interval)    │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─ triggers every 25-50ms
             │
    ┌────────┴────────┬───────────────┬───────────────┐
    │                 │               │               │
┌───▼────┐      ┌─────▼───┐     ┌────▼────┐    ┌────▼────┐
│ Device │      │ Device  │     │ Device  │    │ Device  │
│ Worker │      │ Worker  │     │ Worker  │    │ Worker  │
│   #1   │      │   #2    │     │   #3    │    │   #N    │
└───┬────┘      └─────┬───┘     └────┬────┘    └────┬────┘
    │                 │               │               │
┌───▼─────────────────▼───────────────▼───────────────▼────┐
│              Priority Request Queue (per device)          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  HIGH Priority: API Requests (preemptive)        │    │
│  │  LOW Priority:  Polling Requests (background)    │    │
│  └──────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Unified Polling Scheduler
**File**: `benchmesh-serial-service/src/benchmesh_service/unified_scheduler.py` (new)

**Responsibilities**:
- Single thread that triggers all devices simultaneously
- Configurable polling interval (default: 50ms)
- Enqueues LOW priority polling requests for all devices
- Adaptive timing based on system load

**Key Methods**:
```python
class UnifiedScheduler:
    def __init__(self, interval_ms: float, devices: List[str]):
        self.interval_ms = interval_ms
        self.devices = devices
        self.running = False

    def start(self):
        """Start scheduler thread"""

    def stop(self):
        """Stop scheduler gracefully"""

    def _scheduler_loop(self):
        """Main loop: trigger all devices at interval"""
        while self.running:
            start_time = time.time()

            # Trigger all devices in parallel
            for device_id in self.devices:
                self._enqueue_poll_request(device_id, priority=Priority.LOW)

            # Adaptive sleep until next cycle
            elapsed = time.time() - start_time
            sleep_time = max(0, self.interval_ms/1000 - elapsed)
            time.sleep(sleep_time)
```

#### 2. Priority Request Queue
**File**: `benchmesh-serial-service/src/benchmesh_service/priority_queue.py` (new)

**Responsibilities**:
- Per-device priority queue for requests
- Preemptive scheduling: HIGH priority interrupts LOW priority
- Thread-safe enqueue/dequeue operations

**Key Structure**:
```python
from enum import IntEnum
from queue import PriorityQueue
from dataclasses import dataclass, field
from typing import Any, Callable

class Priority(IntEnum):
    """Priority levels (lower number = higher priority)"""
    HIGH = 1    # API requests (user-triggered)
    LOW = 10    # Background polling

@dataclass(order=True)
class PriorityRequest:
    """A request with priority"""
    priority: Priority
    request: Any = field(compare=False)
    timestamp: float = field(compare=False)

class DeviceRequestQueue:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.queue = PriorityQueue()
        self.current_request: Optional[PriorityRequest] = None
        self.lock = threading.Lock()
        self.interrupt_flag = threading.Event()

    def enqueue(self, request: Any, priority: Priority):
        """Add request to queue"""
        pr = PriorityRequest(priority, request, time.time())
        self.queue.put(pr)

        # If high priority and currently executing low priority, signal interrupt
        if priority == Priority.HIGH and self.current_request:
            if self.current_request.priority == Priority.LOW:
                self.interrupt_flag.set()

    def dequeue(self) -> Optional[PriorityRequest]:
        """Get next request (blocking)"""
        return self.queue.get()

    def should_interrupt(self) -> bool:
        """Check if current low-priority operation should yield"""
        return self.interrupt_flag.is_set()

    def clear_interrupt(self):
        """Clear interrupt flag after yielding"""
        self.interrupt_flag.clear()
```

#### 3. Preemptive Device Worker
**File**: Modify `benchmesh-serial-service/src/benchmesh_service/poll_worker.py`

**Key Changes**:
- Worker processes requests from priority queue
- Polling can be interrupted after each channel query
- API requests execute immediately after current query completes

**Preemptive Polling Logic**:
```python
class PreemptiveDeviceWorker:
    def __init__(self, device_id: str, driver: Any, queue: DeviceRequestQueue):
        self.device_id = device_id
        self.driver = driver
        self.queue = queue

    def run(self):
        """Main worker loop"""
        while True:
            # Get next request from priority queue (blocking)
            request = self.queue.dequeue()
            self.queue.current_request = request

            try:
                if request.request.type == "poll":
                    self._execute_poll_preemptive(request)
                elif request.request.type == "api":
                    self._execute_api(request)
            finally:
                self.queue.current_request = None
                self.queue.clear_interrupt()

    def _execute_poll_preemptive(self, request: PriorityRequest):
        """Execute polling with preemption support"""
        channels = request.request.channels

        for ch in channels:
            # Check for interrupt before each channel query
            if self.queue.should_interrupt():
                # High priority request waiting, yield immediately
                # Put remaining channels back on queue
                remaining = channels[channels.index(ch):]
                self.queue.enqueue(
                    PollRequest(channels=remaining),
                    Priority.LOW
                )
                return

            # Execute single channel query
            result = self.driver.query_channel(ch)
            # Store result...

    def _execute_api(self, request: PriorityRequest):
        """Execute API request (never interrupted)"""
        method = request.request.method
        args = request.request.args
        result = getattr(self.driver, method)(*args)
        request.request.result_callback(result)
```

#### 4. Modified API Layer
**File**: Modify `benchmesh-serial-service/src/benchmesh_service/api.py`

**Key Changes**:
- API endpoints enqueue HIGH priority requests instead of using lock
- Use async/await for response (wait on result_callback)

**Example**:
```python
@app.get("/instruments/{klass}/{device_id}/{channel}/{method}")
async def call_driver_get(klass: str, device_id: str, channel: str, method: str):
    # Validate...

    # Create API request
    result_future = asyncio.Future()

    def result_callback(result):
        result_future.set_result(result)

    api_request = ApiRequest(
        method=resolved_method,
        args=[int(channel)],
        result_callback=result_callback
    )

    # Enqueue with HIGH priority
    queue = _manager.get_device_queue(device_id)
    queue.enqueue(api_request, Priority.HIGH)

    # Wait for result (will be fast - preempts polling)
    result = await result_future

    return {"path": f"/instruments/...", "value": result}
```

### Threading Model

**Before (Current)**:
```
Thread 1: Device-1 worker (independent polling)
Thread 2: Device-2 worker (independent polling)
Thread 3: Device-3 worker (independent polling)
+ API threads (FastAPI workers)
```

**After (Unified)**:
```
Thread 1: Unified Scheduler (triggers all devices)
Thread 2: Device-1 worker (processes priority queue)
Thread 3: Device-2 worker (processes priority queue)
Thread 4: Device-3 worker (processes priority queue)
+ API threads (FastAPI workers, enqueue requests)
```

**Key Difference**:
- Scheduler coordinates WHEN to poll
- Workers execute WHAT to do (polling or API)
- API threads don't block on locks, just enqueue and wait

## Performance Guarantees

### With Preemptive Priority Queue

| Metric | Value | Explanation |
|--------|-------|-------------|
| **UI Update Latency** | 25-50ms | Polling interval (configurable) |
| **API Worst-Case** | 17ms | 2x single query (current query + API query) |
| **API Average** | 13ms | Small wait + API query |
| **API Best-Case** | 8.7ms | No wait, immediate execution |
| **Polling Utilization** | 35-70% | Aggressive but safe |
| **Idle Time** | 30-65% | Plenty of headroom for API |

### Comparison Matrix

| Scenario | Current (2s poll) | Unified (50ms) | Unified (25ms) |
|----------|-------------------|----------------|----------------|
| UI Staleness | 2000ms | 50ms (40x better) | 25ms (80x better) |
| API Worst-Case | 26ms | 17ms | 17ms |
| Utilization | <1% | 35% | 70% |
| Update Rate | 0.5 Hz | 20 Hz | 40 Hz |

## Implementation Phases

### Phase 1: Unified Polling Scheduler (Simple)
**Goal**: Coordinate polling timing without changing worker logic
**Effort**: Low
**Risk**: Low

**Changes**:
- Add `UnifiedScheduler` class
- Scheduler triggers all device workers via flags/events
- Keep existing lock-based synchronization
- Set interval to 500ms (testing)

**Benefits**:
- Synchronized device updates
- Predictable timing
- No API latency impact

### Phase 2: Priority Queue (Non-Preemptive)
**Goal**: API requests jump queue but don't interrupt
**Effort**: Medium
**Risk**: Low

**Changes**:
- Add `DeviceRequestQueue` per device
- Workers process queue instead of self-scheduling
- API enqueues HIGH priority, polling enqueues LOW
- HIGH priority skips to front of queue

**Benefits**:
- API no longer blocked by subsequent polls
- Same worst-case latency, better average case

### Phase 3: Preemptive Scheduling
**Goal**: API interrupts ongoing multi-channel polls
**Effort**: Medium
**Risk**: Medium

**Changes**:
- Add interrupt check between channel queries
- Interrupted polls re-enqueue remaining channels
- API requests execute after current query completes

**Benefits**:
- API worst-case drops to 17ms (vs 26ms)
- Can push utilization to 80-90%
- Best user experience

### Phase 4: Tuning and Optimization
**Goal**: Fine-tune intervals and add monitoring
**Effort**: Low
**Risk**: Low

**Changes**:
- Add metrics collection (latencies, queue depths)
- Adaptive interval based on system load
- Configuration via environment variables
- Grafana dashboards (optional)

## Configuration

### Environment Variables

```bash
# Unified polling interval (milliseconds)
BM_UNIFIED_POLL_INTERVAL=50

# Enable preemptive scheduling
BM_PREEMPTIVE_POLLING=true

# Maximum queue depth before warning
BM_MAX_QUEUE_DEPTH=10

# Enable detailed metrics
BM_POLLING_METRICS=true
```

### Backward Compatibility

- Keep per-device polling as fallback (config flag)
- Gradual migration: test unified on subset of devices first
- Same driver API (no driver changes needed)

## Testing Strategy

### Unit Tests
- `test_priority_queue.py`: Queue ordering, preemption logic
- `test_unified_scheduler.py`: Timing accuracy, device triggering
- `test_preemptive_worker.py`: Interrupt handling, partial poll

### Integration Tests
- `test_api_latency_under_load.py`: API response times at various utilizations
- `test_polling_accuracy.py`: UI update frequency and staleness
- `test_concurrent_api_polling.py`: API + polling interactions

### Performance Tests
- Measure API latency distribution (P50, P95, P99)
- Measure polling utilization over time
- Stress test: 100 API requests/second while polling
- Compare before/after metrics

## Rollout Plan

### Stage 1: Development (Week 1)
- Implement Phase 1 (Unified Scheduler)
- Basic unit tests
- Local testing with 3 devices

### Stage 2: Testing (Week 2)
- Implement Phase 2 (Priority Queue)
- Integration tests
- Test with real hardware

### Stage 3: Preemptive (Week 3)
- Implement Phase 3 (Preemption)
- Performance testing
- Tuning and optimization

### Stage 4: Production (Week 4)
- Deploy with conservative interval (500ms)
- Monitor metrics for 48 hours
- Gradually reduce interval to 50ms
- Final tuning based on real-world data

## Risks and Mitigations

### Risk 1: Preemption Complexity
**Impact**: Medium
**Mitigation**:
- Start with Phase 2 (non-preemptive) which gives 90% of benefit
- Add Phase 3 only if needed
- Comprehensive testing of interrupt logic

### Risk 2: Serial Port Race Conditions
**Impact**: High (if occurs)
**Mitigation**:
- Maintain per-device serialization (never concurrent queries to same port)
- Queue ensures only one operation per device at a time
- Add serial port state validation in tests

### Risk 3: Increased CPU Usage
**Impact**: Low
**Mitigation**:
- Monitor CPU usage during testing
- Adaptive interval scaling under high CPU load
- Even at 50ms, still only 35% utilization

### Risk 4: WebSocket Bandwidth
**Impact**: Low
**Mitigation**:
- Delta updates (only send changed values)
- Configurable WS broadcast rate (can stay at 800ms)
- Compression (gzip) for large registry

## Success Metrics

### Must Have
- ✅ UI update latency < 100ms (P95)
- ✅ API response time < 50ms (P99)
- ✅ No serial communication errors
- ✅ CPU usage < 20% (on typical hardware)

### Nice to Have
- 🎯 UI update latency < 50ms (P95)
- 🎯 API response time < 20ms (P99)
- 🎯 Polling utilization 50-70%
- 🎯 Support for 20+ concurrent devices

## References

- [Performance Analysis Script](../scripts/performance_analysis.py)
- [Unified Polling Analysis](../scripts/unified_polling_analysis.py)
- [Implementation Philosophy](./IMPLEMENTATION_PHILOSOPHY.md)

## Approval & Sign-off

**Recommendation**: Implement Phase 1 & 2 immediately (low risk, high value)
- Phase 1: Unified scheduler for synchronized updates
- Phase 2: Priority queue for better API responsiveness

**Phase 3 (Preemptive)**: Implement only if Phase 2 results show need for further improvement.

---

**Author**: Claude Code
**Date**: 2025-10-15
**Status**: Design Complete - Awaiting Approval
