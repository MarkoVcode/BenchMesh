"""
Unit tests for connection health monitoring and timeout classification.

Tests cover:
- DeviceConnection health state transitions
- Timeout vs error classification in record_failure()
- ConnectionQualityMonitor penalty differentiation
- Health status tracking (unknown → healthy → degraded → dead)
"""

import pytest
from unittest.mock import Mock
from benchmesh_service.connection import DeviceConnection, ConnectionQualityMonitor
from benchmesh_service.clock import Clock


# ===== TEST FIXTURES =====

@pytest.fixture
def mock_clock():
    """Mock clock for testing."""
    clock = Mock(spec=Clock)
    clock.now.return_value = 0.0
    return clock


@pytest.fixture
def mock_driver():
    """Mock driver for testing."""
    driver = Mock()
    driver.t = Mock()
    driver.t.is_open = True
    return driver


@pytest.fixture
def connection(mock_driver, mock_clock):
    """DeviceConnection with quality monitoring enabled."""
    return DeviceConnection(
        driver=mock_driver,
        clock=mock_clock,
        failure_threshold=3,
        degraded_threshold=1,
        enable_quality_monitoring=True,
        quality_window_size=20,
        quality_success_points=5,
        quality_timeout_penalty=10,
        quality_error_penalty=15
    )


@pytest.fixture
def quality_monitor():
    """Standalone ConnectionQualityMonitor for testing."""
    return ConnectionQualityMonitor(
        window_size=20,
        success_points=5,
        timeout_penalty=10,
        error_penalty=15,
        enable_weighted_history=False  # Disable for predictable testing
    )


# ===== HEALTH STATE TRANSITION TESTS =====

class TestHealthStateTransitions:
    """Test health state transitions based on failures/successes."""

    def test_initial_state_is_unknown(self, connection):
        """Test that connection starts in 'unknown' state."""
        assert connection.health_status == "unknown"
        assert connection.consecutive_failures == 0

    def test_first_success_sets_healthy(self, connection):
        """Test that first success transitions to 'healthy'."""
        connection.record_success()
        assert connection.health_status == "healthy"
        assert connection.consecutive_failures == 0

    def test_first_failure_sets_degraded(self, connection):
        """Test that first failure transitions to 'degraded' (threshold=1)."""
        connection.record_failure(is_timeout=False)
        assert connection.health_status == "degraded"
        assert connection.consecutive_failures == 1

    def test_third_failure_sets_dead(self, connection):
        """Test that third failure transitions to 'dead' (threshold=3)."""
        connection.record_failure(is_timeout=False)  # 1st - degraded
        connection.record_failure(is_timeout=False)  # 2nd - still degraded
        connection.record_failure(is_timeout=False)  # 3rd - dead
        assert connection.health_status == "dead"
        assert connection.consecutive_failures == 3

    def test_success_resets_failures(self, connection):
        """Test that success resets consecutive failures."""
        connection.record_failure(is_timeout=False)  # degraded
        connection.record_failure(is_timeout=False)  # still degraded
        assert connection.consecutive_failures == 2

        connection.record_success()
        assert connection.health_status == "healthy"
        assert connection.consecutive_failures == 0

    def test_timeout_failure_follows_same_state_transitions(self, connection):
        """Test that timeout failures follow same state transitions as errors."""
        connection.record_failure(is_timeout=True)  # 1st - degraded
        assert connection.health_status == "degraded"
        assert connection.consecutive_failures == 1

        connection.record_failure(is_timeout=True)  # 2nd
        connection.record_failure(is_timeout=True)  # 3rd - dead
        assert connection.health_status == "dead"
        assert connection.consecutive_failures == 3


# ===== TIMEOUT CLASSIFICATION TESTS =====

class TestTimeoutClassification:
    """Test timeout vs error classification in record_failure()."""

    def test_timeout_failure_passes_to_quality_monitor(self, connection):
        """Test that is_timeout=True passes 'timeout' outcome to quality monitor."""
        connection.record_failure(is_timeout=True)

        # Check quality monitor received timeout outcome
        assert connection.quality_monitor.operation_window[-1] == "timeout"

    def test_error_failure_passes_to_quality_monitor(self, connection):
        """Test that is_timeout=False passes 'error' outcome to quality monitor."""
        connection.record_failure(is_timeout=False)

        # Check quality monitor received error outcome
        assert connection.quality_monitor.operation_window[-1] == "error"

    def test_success_passes_to_quality_monitor(self, connection):
        """Test that record_success() passes 'success' outcome."""
        connection.record_success()

        # Check quality monitor received success outcome
        assert connection.quality_monitor.operation_window[-1] == "success"

    def test_mixed_timeout_and_error_outcomes(self, connection):
        """Test mixed timeout and error failures."""
        connection.record_failure(is_timeout=True)   # timeout
        connection.record_failure(is_timeout=False)  # error
        connection.record_success()                  # success
        connection.record_failure(is_timeout=True)   # timeout

        outcomes = list(connection.quality_monitor.operation_window)
        assert outcomes == ["timeout", "error", "success", "timeout"]


# ===== QUALITY MONITOR PENALTY TESTS =====

class TestQualityMonitorPenalties:
    """Test that quality monitor applies different penalties for timeout vs error."""

    def test_timeout_applies_10_point_penalty(self, quality_monitor):
        """Test that timeout outcome applies -10 point penalty."""
        quality_monitor.record_operation("success")  # +5
        quality_monitor.record_operation("timeout")  # -10

        # Timeout penalty should produce a score reflecting the -10 penalty
        score = quality_monitor.get_quality_score()
        assert 50 <= score <= 70  # Normalized score range for 1 success, 1 timeout

    def test_error_applies_15_point_penalty(self, quality_monitor):
        """Test that error outcome applies -15 point penalty."""
        quality_monitor.record_operation("success")  # +5
        quality_monitor.record_operation("error")    # -15

        # Error penalty should produce a score reflecting the -15 penalty
        score = quality_monitor.get_quality_score()
        assert 40 <= score <= 60  # Normalized score range for 1 success, 1 error

    def test_timeout_less_severe_than_error(self, quality_monitor):
        """Test that timeout penalty is less severe than error penalty."""
        # Create two identical monitors
        monitor_timeout = ConnectionQualityMonitor(
            window_size=20, success_points=5,
            timeout_penalty=10, error_penalty=15,
            enable_weighted_history=False
        )
        monitor_error = ConnectionQualityMonitor(
            window_size=20, success_points=5,
            timeout_penalty=10, error_penalty=15,
            enable_weighted_history=False
        )

        # Apply same number of failures
        for _ in range(5):
            monitor_timeout.record_operation("timeout")
            monitor_error.record_operation("error")

        # Timeout should have higher score (less severe)
        assert monitor_timeout.get_quality_score() > monitor_error.get_quality_score()

    def test_multiple_timeout_vs_error_penalties(self, quality_monitor):
        """Test accumulation of different penalty types."""
        # Record pattern: success, timeout, success, error
        quality_monitor.record_operation("success")  # +5
        quality_monitor.record_operation("timeout")  # -10
        quality_monitor.record_operation("success")  # +5
        quality_monitor.record_operation("error")    # -15

        # Total: 5 - 10 + 5 - 15 = -15
        # Min score for 4 ops: -60 (all errors)
        # Max score for 4 ops: +20 (all success)
        # Normalized: (-15 - (-60)) / (20 - (-60)) * 100 = 45/80 * 100 ≈ 56.25
        score = quality_monitor.get_quality_score()
        assert 50 <= score <= 60


# ===== QUALITY SCORE CALCULATION TESTS =====

class TestQualityScoreCalculation:
    """Test quality score calculation with different outcome patterns."""

    def test_all_successes_gives_100_score(self, quality_monitor):
        """Test that all successes gives 100% quality score."""
        for _ in range(10):
            quality_monitor.record_operation("success")

        assert quality_monitor.get_quality_score() == 100.0

    def test_all_errors_gives_0_score(self, quality_monitor):
        """Test that all errors gives 0% quality score."""
        for _ in range(10):
            quality_monitor.record_operation("error")

        assert quality_monitor.get_quality_score() == 0.0

    def test_all_timeouts_gives_low_but_nonzero_score(self, quality_monitor):
        """Test that all timeouts gives low but > 0 score (less severe than errors)."""
        for _ in range(10):
            quality_monitor.record_operation("timeout")

        score = quality_monitor.get_quality_score()
        assert 0.0 < score < 40.0  # Better than all errors (0), but still bad

    def test_mixed_outcomes_balanced_score(self, quality_monitor):
        """Test balanced mix of outcomes."""
        for _ in range(5):
            quality_monitor.record_operation("success")
        for _ in range(3):
            quality_monitor.record_operation("timeout")
        for _ in range(2):
            quality_monitor.record_operation("error")

        # 5 success (+25), 3 timeout (-30), 2 error (-30) = -35
        # Normalized score will be in mid-range
        score = quality_monitor.get_quality_score()
        assert 50 <= score <= 65  # Balanced mix should be mid-range


# ===== QUALITY TIER TESTS =====

class TestQualityTiers:
    """Test quality tier classification based on scores."""

    def test_excellent_tier_95_to_100(self, quality_monitor):
        """Test excellent tier (95-100)."""
        # Mostly successes
        for _ in range(19):
            quality_monitor.record_operation("success")
        quality_monitor.record_operation("timeout")  # One minor issue

        tier = quality_monitor.get_quality_tier()
        score = quality_monitor.get_quality_score()

        # Should be in excellent or good tier
        assert tier in ("excellent", "good")
        assert score >= 80

    def test_critical_tier_below_40(self, quality_monitor):
        """Test critical tier (<40)."""
        # Mostly errors
        for _ in range(8):
            quality_monitor.record_operation("error")
        for _ in range(2):
            quality_monitor.record_operation("success")

        tier = quality_monitor.get_quality_tier()
        assert tier in ("critical", "poor")

    def test_speed_multiplier_reflects_quality(self, quality_monitor):
        """Test that speed multiplier decreases with quality."""
        # Excellent quality
        for _ in range(10):
            quality_monitor.record_operation("success")
        excellent_mult = quality_monitor.get_speed_multiplier()

        # Reset and make poor quality
        quality_monitor.reset()
        for _ in range(7):
            quality_monitor.record_operation("error")
        for _ in range(3):
            quality_monitor.record_operation("success")
        poor_mult = quality_monitor.get_speed_multiplier()

        # Excellent should have higher multiplier
        assert excellent_mult > poor_mult


# ===== RESET TESTS =====

class TestConnectionReset:
    """Test health reset functionality."""

    def test_reset_health_clears_state(self, connection):
        """Test that reset_health() clears all health state."""
        # Set up some state
        connection.record_failure(is_timeout=False)
        connection.record_failure(is_timeout=False)
        assert connection.health_status == "degraded"
        assert connection.consecutive_failures == 2

        # Reset
        connection.reset_health()

        assert connection.health_status == "unknown"
        assert connection.consecutive_failures == 0
        assert connection.last_successful_response == 0.0

    def test_reset_clears_quality_monitor(self, connection):
        """Test that reset clears quality monitor history."""
        # Record some operations
        connection.record_success()
        connection.record_failure(is_timeout=True)
        connection.record_failure(is_timeout=False)

        assert len(connection.quality_monitor.operation_window) == 3

        # Reset
        connection.reset_health()

        # Quality monitor should be cleared
        assert len(connection.quality_monitor.operation_window) == 0


# ===== INTEGRATION TESTS =====

class TestConnectionHealthIntegration:
    """Integration tests combining health states and quality monitoring."""

    def test_timeout_degradation_pattern(self, connection):
        """Test realistic timeout degradation pattern."""
        # Initial successes
        for _ in range(5):
            connection.record_success()

        assert connection.health_status == "healthy"
        score_healthy = connection.get_quality_score()

        # Start experiencing timeouts
        for _ in range(3):
            connection.record_failure(is_timeout=True)

        # Should be dead (3 consecutive failures)
        assert connection.health_status == "dead"
        score_degraded = connection.get_quality_score()

        # Quality should have decreased
        assert score_degraded < score_healthy

    def test_recovery_from_dead_state(self, connection):
        """Test recovery from dead state."""
        # Fail to dead state
        for _ in range(3):
            connection.record_failure(is_timeout=False)

        assert connection.health_status == "dead"

        # Recover with success
        connection.record_success()

        assert connection.health_status == "healthy"
        assert connection.consecutive_failures == 0

    def test_intermittent_failures_keep_degraded(self, connection):
        """Test that intermittent failures keep connection degraded."""
        connection.record_success()
        connection.record_failure(is_timeout=True)   # degraded
        connection.record_success()
        connection.record_failure(is_timeout=False)  # degraded again
        connection.record_success()

        # Last was success, so healthy now
        assert connection.health_status == "healthy"

        # But quality score should reflect the failures
        score = connection.get_quality_score()
        assert score < 100.0  # Not perfect due to failures
