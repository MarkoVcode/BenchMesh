import time
from unittest.mock import Mock, patch
import pytest
from benchmesh_service.unified_scheduler import UnifiedScheduler
from benchmesh_service.priority_queue import DeviceRequestQueue
from benchmesh_service.connection import DeviceConnection


class FakeDeviceConnection:
    """Mock DeviceConnection for testing circuit breaker"""
    def __init__(self, health_status="healthy", consecutive_failures=0):
        self.health_status = health_status
        self.consecutive_failures = consecutive_failures

    def is_healthy(self):
        """Match real DeviceConnection.is_healthy() - True for healthy/degraded, False for dead/unknown"""
        return self.health_status in ("healthy", "degraded")


def test_circuit_breaker_skips_dead_device():
    """Test that circuit breaker prevents polling for dead devices"""
    # Setup scheduler with dead device
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    dead_conn = FakeDeviceConnection(health_status="dead", consecutive_failures=5)

    scheduler.device_connections[device_id] = dead_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Manually trigger check
    scheduler._check_and_trigger_devices()

    # Queue should be empty (no poll request enqueued)
    assert queue.qsize() == 0
    # Skip counter should increment
    assert scheduler.skipped_polls[device_id] > 0


def test_circuit_breaker_allows_degraded_device():
    """Test that degraded devices still get polled (they're responding, just with failures)"""
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    degraded_conn = FakeDeviceConnection(health_status="degraded", consecutive_failures=2)

    scheduler.device_connections[device_id] = degraded_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Manually trigger check
    scheduler._check_and_trigger_devices()

    # Queue should have poll request (degraded devices still get polled)
    assert queue.qsize() == 1
    # No skips for degraded device (it's still healthy enough to poll)
    assert scheduler.skipped_polls[device_id] == 0


def test_circuit_breaker_skips_unknown_device():
    """Test that circuit breaker prevents polling for unknown health status"""
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    unknown_conn = FakeDeviceConnection(health_status="unknown", consecutive_failures=0)

    scheduler.device_connections[device_id] = unknown_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Manually trigger check
    scheduler._check_and_trigger_devices()

    # Queue should be empty (no poll request enqueued)
    assert queue.qsize() == 0
    # Skip counter should increment
    assert scheduler.skipped_polls[device_id] > 0


def test_healthy_device_gets_polled():
    """Test that healthy devices get poll requests enqueued"""
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    healthy_conn = FakeDeviceConnection(health_status="healthy", consecutive_failures=0)

    scheduler.device_connections[device_id] = healthy_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Manually trigger check
    scheduler._check_and_trigger_devices()

    # Queue should have one poll request
    assert queue.qsize() == 1
    # No skips for healthy device
    assert scheduler.skipped_polls[device_id] == 0


def test_queue_draining_for_unhealthy_device():
    """Test that queue is drained when unhealthy device has backlog"""
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    dead_conn = FakeDeviceConnection(health_status="dead", consecutive_failures=5)

    scheduler.device_connections[device_id] = dead_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Manually add 8 items to queue (exceeds drain threshold of 5)
    from benchmesh_service.priority_queue import PollRequest, Priority
    for i in range(8):
        poll_req = PollRequest(type="poll", device_id=device_id, now=time.time())
        queue.enqueue(poll_req, Priority.LOW)

    initial_queue_size = queue.qsize()
    assert initial_queue_size == 8

    # Trigger check - should drain queue
    scheduler._check_and_trigger_devices()

    # Queue should be drained
    assert queue.qsize() == 0


def test_queue_not_drained_for_small_backlog():
    """Test that queue is NOT drained when backlog is below threshold (<=5)"""
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    dead_conn = FakeDeviceConnection(health_status="dead", consecutive_failures=5)

    scheduler.device_connections[device_id] = dead_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Add only 3 items to queue (below drain threshold of 5)
    from benchmesh_service.priority_queue import PollRequest, Priority
    for i in range(3):
        poll_req = PollRequest(type="poll", device_id=device_id, now=time.time())
        queue.enqueue(poll_req, Priority.LOW)

    initial_queue_size = queue.qsize()
    assert initial_queue_size == 3

    # Trigger check - should NOT drain queue
    scheduler._check_and_trigger_devices()

    # Queue should still have items (not drained)
    assert queue.qsize() == 3


def test_circuit_breaker_checked_before_queue_depth():
    """
    Test that circuit breaker is checked BEFORE queue depth.

    This is critical to prevent log spam when a dead device has accumulated
    a queue backlog. The circuit breaker should prevent any queue depth
    warnings from being logged.
    """
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    dead_conn = FakeDeviceConnection(health_status="dead", consecutive_failures=5)

    scheduler.device_connections[device_id] = dead_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Fill queue beyond max_queue_depth threshold
    from benchmesh_service.priority_queue import PollRequest, Priority
    for i in range(15):  # Exceeds max_queue_depth of 10
        poll_req = PollRequest(type="poll", device_id=device_id, now=time.time())
        queue.enqueue(poll_req, Priority.LOW)

    assert queue.qsize() == 15

    # Mock logger to verify no queue depth warnings
    with patch('benchmesh_service.unified_scheduler.logger') as mock_logger:
        # Trigger check
        scheduler._check_and_trigger_devices()

        # Should log about dead device, not queue depth
        # Check that no warnings about queue depth were logged
        warning_calls = [call for call in mock_logger.warning.call_args_list
                        if 'queue depth' in str(call)]
        assert len(warning_calls) == 0, "Should not log queue depth warnings for dead device"

        # Should have logged info about dead device or drained queue
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) > 0, "Should log info about dead device"


def test_queue_depth_warning_for_healthy_overloaded_device():
    """Test that queue depth warnings are still logged for healthy but overloaded devices"""
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    healthy_conn = FakeDeviceConnection(health_status="healthy", consecutive_failures=0)

    scheduler.device_connections[device_id] = healthy_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Fill queue beyond max_queue_depth threshold
    from benchmesh_service.priority_queue import PollRequest, Priority
    for i in range(15):  # Exceeds max_queue_depth of 10
        poll_req = PollRequest(type="poll", device_id=device_id, now=time.time())
        queue.enqueue(poll_req, Priority.LOW)

    assert queue.qsize() == 15

    # Mock logger to verify queue depth warning IS logged
    with patch('benchmesh_service.unified_scheduler.logger') as mock_logger:
        # Trigger check
        scheduler._check_and_trigger_devices()

        # Should log queue depth warning for healthy device
        warning_calls = [call for call in mock_logger.warning.call_args_list
                        if 'queue depth' in str(call)]
        assert len(warning_calls) == 1, "Should log queue depth warning for healthy overloaded device"


def test_no_polling_without_device_connection():
    """Test that devices without connection tracking still get polled (backward compatibility)"""
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)

    # Register device WITHOUT adding to device_connections (legacy mode)
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Manually trigger check
    scheduler._check_and_trigger_devices()

    # Queue should have poll request (backward compatibility)
    assert queue.qsize() == 1
    # No skips
    assert scheduler.skipped_polls[device_id] == 0


def test_registry_cleared_when_device_becomes_unhealthy():
    """Test that registry is cleared when device transitions from healthy to unhealthy"""
    from benchmesh_service.registry import DeviceRegistry

    # Create registry with device data
    registry = DeviceRegistry()
    registry.set_idn("test-device", "FAKE,IDN,12345")
    registry.update("test-device", "status_ch1", {"voltage": 5.0}, klass="PSU")

    # Verify registry has data
    assert registry.data["test-device"]["IDN"] == "FAKE,IDN,12345"
    assert registry.data["test-device"]["PSU"]["status_ch1"]["voltage"] == 5.0

    # Create scheduler with registry
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10, registry=registry)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)

    # Start with healthy device
    healthy_conn = FakeDeviceConnection(health_status="healthy", consecutive_failures=0)
    scheduler.device_connections[device_id] = healthy_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Trigger check with healthy device - should poll normally
    scheduler._check_and_trigger_devices()
    assert queue.qsize() == 1

    # Change device to dead
    dead_conn = FakeDeviceConnection(health_status="dead", consecutive_failures=5)
    scheduler.device_connections[device_id] = dead_conn

    # Reset last_poll_time to ensure timing check passes
    with scheduler._lock:
        scheduler.last_poll_time[device_id] = 0.0

    # Trigger check again - should detect health transition and clear registry
    scheduler._check_and_trigger_devices()

    # Registry should be cleared (no IDN)
    assert "IDN" not in registry.data["test-device"]
    # Status should also be cleared
    assert "PSU" not in registry.data["test-device"] or "status_ch1" not in registry.data["test-device"].get("PSU", {})


def test_registry_not_cleared_repeatedly():
    """Test that registry is only cleared once on health transition, not repeatedly"""
    from benchmesh_service.registry import DeviceRegistry

    # Create registry with device data
    registry = DeviceRegistry()
    registry.set_idn("test-device", "FAKE,IDN,12345")

    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10, registry=registry)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)
    dead_conn = FakeDeviceConnection(health_status="dead", consecutive_failures=5)

    scheduler.device_connections[device_id] = dead_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # First check - should clear registry
    scheduler._check_and_trigger_devices()
    assert "IDN" not in registry.data[device_id]

    # Re-add IDN to simulate registry being populated again somehow
    registry.set_idn(device_id, "FAKE,IDN,12345")

    # Second check - should NOT clear registry again (device already marked as unhealthy)
    scheduler._check_and_trigger_devices()
    assert registry.data[device_id]["IDN"] == "FAKE,IDN,12345"  # Still present


def test_registry_cleared_on_recovery_detection():
    """Test that device recovery is detected and logged"""
    from benchmesh_service.registry import DeviceRegistry

    registry = DeviceRegistry()
    scheduler = UnifiedScheduler(interval_ms=50.0, max_queue_depth=10, registry=registry)

    device_id = "test-device"
    queue = DeviceRequestQueue(device_id)

    # Start with dead device
    dead_conn = FakeDeviceConnection(health_status="dead", consecutive_failures=5)
    scheduler.device_connections[device_id] = dead_conn
    scheduler.register_device(device_id, queue, interval_ms=50.0)

    # Trigger check with dead device
    scheduler._check_and_trigger_devices()
    assert scheduler.device_was_healthy[device_id] is False

    # Change device to healthy
    healthy_conn = FakeDeviceConnection(health_status="healthy", consecutive_failures=0)
    scheduler.device_connections[device_id] = healthy_conn

    # Trigger check - should detect recovery
    scheduler._check_and_trigger_devices()
    assert scheduler.device_was_healthy[device_id] is True
    assert queue.qsize() == 1  # Should resume polling
