"""
Integration tests for poll_status health monitoring flow.

Tests the complete flow from driver poll_status() exceptions to health state changes:
1. Driver raises TimeoutError or other exception
2. Worker catches exception and classifies as timeout vs error
3. Connection.record_failure(is_timeout=True/False) called
4. Health state transitions (unknown → healthy → degraded → dead)
5. Quality monitor tracks timeout vs error penalties

This validates the entire health monitoring chain works correctly.
"""

import pytest
import time
from unittest.mock import Mock
from benchmesh_service.poll_worker import DeviceWorker
from benchmesh_service.registry import DeviceRegistry
from benchmesh_service.manifest_resolver import ManifestResolver
from benchmesh_service.connection import DeviceConnection
from benchmesh_service.clock import Clock


# ===== TEST FIXTURES =====

@pytest.fixture
def mock_clock():
    """Mock clock for testing."""
    clock = Mock(spec=Clock)
    clock.now.return_value = time.time()
    return clock


@pytest.fixture
def device_config():
    """Mock device configuration."""
    return {
        'id': 'test-device',
        'name': 'Test Device',
        'driver': 'test_driver',
        'port': '/dev/ttyTEST',
        'baud': 115200,
        'serial': '8N1'
    }


@pytest.fixture
def registry():
    """Device registry with IDN set (required for polling)."""
    from unittest.mock import Mock
    reg = DeviceRegistry({'test-device': {'IDN': 'TEST,DEVICE,SN:12345,V1.0'}})
    # Mock clear_disconnected to preserve IDN for testing multiple failures
    reg.clear_disconnected = Mock()
    return reg


@pytest.fixture
def resolver():
    """Manifest resolver with mocked methods to avoid loading test_driver manifest."""
    from unittest.mock import Mock
    resolver = Mock(spec=ManifestResolver)
    resolver.get_poll_method.return_value = 'poll_status'  # Return default poll method
    resolver.has_multi_class_polling.return_value = False  # Use per-class polling
    return resolver


# ===== MOCK DRIVERS =====

class HealthyDriver:
    """Driver that successfully returns poll data."""

    def poll_status(self, channel: int):
        return {"STATUS": "OK", "CHANNEL": channel}


class TimeoutDriver:
    """Driver that raises TimeoutError."""

    def poll_status(self, channel: int):
        raise TimeoutError("Device not responding")


class ErrorDriver:
    """Driver that raises generic exception."""

    def poll_status(self, channel: int):
        raise RuntimeError("Communication error")


class EmptyResponseDriver:
    """Driver that returns empty dict (device off)."""

    def poll_status(self, channel: int):
        return {}


class IntermittentTimeoutDriver:
    """Driver that alternates between success and timeout."""

    def __init__(self):
        self.call_count = 0

    def poll_status(self, channel: int):
        self.call_count += 1
        if self.call_count % 2 == 0:
            raise TimeoutError("Intermittent timeout")
        return {"STATUS": "OK", "CHANNEL": channel}


# ===== INTEGRATION TESTS =====

class TestPollHealthIntegration:
    """Integration tests for poll_status → health monitoring flow."""

    def test_successful_poll_marks_healthy(self, device_config, registry, resolver, mock_clock):
        """Test that successful poll marks connection healthy."""
        driver = HealthyDriver()
        connection = DeviceConnection(
            driver=driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        worker = DeviceWorker(
            dev=device_config,
            driver=driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},  # Bypass manifest loading
            interval_override={"TEST": 0.0}  # Poll immediately
        )

        # Initial state
        assert connection.health_status == "unknown"

        # Poll once
        now = time.time()
        worker.run_once(now)

        # Should be marked healthy
        assert connection.health_status == "healthy"
        assert connection.consecutive_failures == 0

        # Quality should be good
        assert connection.get_quality_score() > 90.0

    def test_timeout_error_marks_degraded(self, device_config, registry, resolver, mock_clock):
        """Test that TimeoutError marks connection degraded."""
        driver = TimeoutDriver()
        connection = DeviceConnection(
            driver=driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        worker = DeviceWorker(
            dev=device_config,
            driver=driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        # Poll once - should catch TimeoutError
        now = time.time()
        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(now)

        # Should be marked degraded (threshold=1)
        assert connection.health_status == "degraded"
        assert connection.consecutive_failures == 1

        # Quality monitor should have recorded timeout
        assert connection.quality_monitor.operation_window[-1] == "timeout"

    def test_three_timeouts_mark_dead(self, device_config, registry, resolver, mock_clock):
        """Test that 3 consecutive TimeoutErrors mark connection dead."""
        driver = TimeoutDriver()
        connection = DeviceConnection(
            driver=driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        worker = DeviceWorker(
            dev=device_config,
            driver=driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        now = time.time()

        # First timeout - degraded
        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(now)
        assert connection.health_status == "degraded"

        # Second timeout - still degraded
        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(now + 1)
        assert connection.health_status == "degraded"

        # Third timeout - dead
        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(now + 2)
        assert connection.health_status == "dead"
        assert connection.consecutive_failures == 3

    def test_generic_error_marks_degraded_with_error_outcome(self, device_config, registry, resolver, mock_clock):
        """Test that generic exception marks degraded with error outcome (not timeout)."""
        driver = ErrorDriver()
        connection = DeviceConnection(
            driver=driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        worker = DeviceWorker(
            dev=device_config,
            driver=driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        # Poll once - should catch RuntimeError
        now = time.time()
        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(now)

        # Should be marked degraded
        assert connection.health_status == "degraded"

        # Quality monitor should have recorded error (not timeout)
        assert connection.quality_monitor.operation_window[-1] == "error"

    def test_empty_response_marks_degraded(self, device_config, registry, resolver, mock_clock):
        """Test that empty dict response marks degraded."""
        driver = EmptyResponseDriver()
        connection = DeviceConnection(
            driver=driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        worker = DeviceWorker(
            dev=device_config,
            driver=driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        # Poll once - should detect empty response
        now = time.time()
        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(now)

        # Should be marked degraded (empty response = failure)
        assert connection.health_status == "degraded"
        assert connection.consecutive_failures == 1

    def test_timeout_has_less_quality_penalty_than_error(self, device_config, registry, resolver, mock_clock):
        """Test that timeout penalty (-10) is less severe than error penalty (-15)."""
        # Create two connections with different failure types
        timeout_driver = TimeoutDriver()
        error_driver = ErrorDriver()

        timeout_connection = DeviceConnection(
            driver=timeout_driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        error_connection = DeviceConnection(
            driver=error_driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        timeout_worker = DeviceWorker(
            dev=device_config,
            driver=timeout_driver,
            registry=registry,
            resolver=resolver,
            connection=timeout_connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        error_worker = DeviceWorker(
            dev=device_config,
            driver=error_driver,
            registry=registry,
            resolver=resolver,
            connection=error_connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        now = time.time()

        # Apply same number of failures to both
        for i in range(2):  # Don't hit dead threshold
            with pytest.raises(RuntimeError, match="poll_empty"):
                timeout_worker.run_once(now + i)
            with pytest.raises(RuntimeError, match="poll_empty"):
                error_worker.run_once(now + i)

        # Timeout should have higher quality score (less severe)
        timeout_score = timeout_connection.get_quality_score()
        error_score = error_connection.get_quality_score()

        assert timeout_score > error_score, "Timeout should be less severe than error"

    def test_intermittent_timeouts_affect_quality_but_not_health(self, device_config, registry, resolver, mock_clock):
        """Test that intermittent timeouts degrade quality but recover health."""
        driver = IntermittentTimeoutDriver()
        connection = DeviceConnection(
            driver=driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        worker = DeviceWorker(
            dev=device_config,
            driver=driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        now = time.time()

        # Poll sequence: success, timeout, success, timeout
        worker.run_once(now)  # Success (call 1)
        assert connection.health_status == "healthy"

        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(now + 1)  # Timeout (call 2)
        assert connection.health_status == "degraded"

        worker.run_once(now + 2)  # Success (call 3)
        assert connection.health_status == "healthy"  # Recovered

        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(now + 3)  # Timeout (call 4)
        assert connection.health_status == "degraded"

        # Health recovered each time, but quality should reflect the failures
        quality = connection.get_quality_score()
        assert quality < 100.0, "Quality should be affected by timeouts"
        assert quality > 0.0, "Quality should not be zero (some successes)"

    def test_recovery_from_dead_to_healthy(self, device_config, registry, resolver, mock_clock):
        """Test complete recovery from dead state to healthy."""
        # Start with timeout driver
        timeout_driver = TimeoutDriver()
        connection = DeviceConnection(
            driver=timeout_driver,
            clock=mock_clock,
            failure_threshold=3,
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        timeout_worker = DeviceWorker(
            dev=device_config,
            driver=timeout_driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        now = time.time()

        # Fail to dead state
        for i in range(3):
            with pytest.raises(RuntimeError, match="poll_empty"):
                timeout_worker.run_once(now + i)

        assert connection.health_status == "dead"
        dead_quality = connection.get_quality_score()

        # Switch to healthy driver (simulating device recovery)
        healthy_driver = HealthyDriver()
        connection.driver = healthy_driver
        healthy_worker = DeviceWorker(
            dev=device_config,
            driver=healthy_driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        # Poll with healthy driver
        healthy_worker.run_once(now + 3)

        # Should recover to healthy
        assert connection.health_status == "healthy"
        assert connection.consecutive_failures == 0

        # Quality should improve
        recovered_quality = connection.get_quality_score()
        assert recovered_quality > dead_quality

    def test_quality_penalties_accumulate_correctly(self, device_config, registry, resolver, mock_clock):
        """Test that quality penalties accumulate correctly for different failure types."""
        # Create driver that we can control
        class ControllableDriver:
            def __init__(self):
                self.behavior = "success"

            def poll_status(self, channel: int):
                if self.behavior == "timeout":
                    raise TimeoutError("Controlled timeout")
                elif self.behavior == "error":
                    raise RuntimeError("Controlled error")
                elif self.behavior == "empty":
                    return {}
                return {"STATUS": "OK"}

        driver = ControllableDriver()
        connection = DeviceConnection(
            driver=driver,
            clock=mock_clock,
            failure_threshold=10,  # High threshold to avoid dead state
            degraded_threshold=1,
            enable_quality_monitoring=True
        )

        worker = DeviceWorker(
            dev=device_config,
            driver=driver,
            registry=registry,
            resolver=resolver,
            connection=connection,
            channels_override={"TEST": 1},
            interval_override={"TEST": 0.0}
        )

        now = time.time()
        t = now

        # Pattern: 3 success, 1 timeout, 2 success, 1 error
        for _ in range(3):
            driver.behavior = "success"
            worker.run_once(t)
            t += 1

        driver.behavior = "timeout"
        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(t)
        t += 1

        for _ in range(2):
            driver.behavior = "success"
            worker.run_once(t)
            t += 1

        driver.behavior = "error"
        with pytest.raises(RuntimeError, match="poll_empty"):
            worker.run_once(t)

        # Verify outcomes recorded correctly
        outcomes = list(connection.quality_monitor.operation_window)
        assert outcomes.count("success") == 5
        assert outcomes.count("timeout") == 1
        assert outcomes.count("error") == 1

        # Quality should be good but not perfect
        quality = connection.get_quality_score()
        assert 60 < quality < 90  # Some failures, but mostly successes
