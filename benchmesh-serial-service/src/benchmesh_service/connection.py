from __future__ import annotations
from typing import Optional, Any, Literal
from .clock import Clock

# Health status states for device connection
HealthStatus = Literal["unknown", "healthy", "degraded", "dead"]


from collections import deque
from typing import Literal

# Operation outcome types for quality monitoring
OperationOutcome = Literal["success", "timeout", "error"]


class ConnectionQualityMonitor:
    """
    Monitors connection quality over a rolling window of operations.

    Tracks success/failure patterns to calculate a quality score that can
    be used for adaptive throttling decisions.

    Quality Score:
    - Calculated from rolling window of recent operations
    - Success: +5 points
    - Timeout: -10 points
    - Error: -15 points

    Phase 3 Enhancements:
    - Trend detection: Identifies improving vs degrading patterns
    - Weighted recent history: Recent operations weighted more heavily
    - Quality threshold triggers: Automatic behaviors at different tiers

    Quality Tiers:
    - excellent (95-100): 1.0x speed multiplier
    - good (80-95): 0.9x speed multiplier
    - fair (60-80): 0.7x speed multiplier
    - poor (40-60): 0.5x speed multiplier
    - critical (<40): 0.25x speed multiplier
    """

    def __init__(self, window_size: int = 20, success_points: int = 5,
                 timeout_penalty: int = 10, error_penalty: int = 15,
                 enable_weighted_history: bool = True, recent_weight_factor: float = 2.0):
        """
        Initialize quality monitor.

        Args:
            window_size: Number of recent operations to track
            success_points: Points awarded for successful operation
            timeout_penalty: Points deducted for timeout
            error_penalty: Points deducted for error
            enable_weighted_history: Phase 3: Weight recent operations more heavily
            recent_weight_factor: Phase 3: Multiplier for recent 25% of window
        """
        self.window_size = window_size
        self.success_points = success_points
        self.timeout_penalty = timeout_penalty
        self.error_penalty = error_penalty
        self.enable_weighted_history = enable_weighted_history
        self.recent_weight_factor = recent_weight_factor

        # Rolling window of operation outcomes
        self.operation_window: deque[OperationOutcome] = deque(maxlen=window_size)

        # Phase 3: Trend tracking
        self.quality_history: deque[float] = deque(maxlen=10)  # Track last 10 quality scores for trend
        
    def record_operation(self, outcome: OperationOutcome) -> None:
        """
        Record an operation outcome.

        Args:
            outcome: 'success', 'timeout', or 'error'
        """
        self.operation_window.append(outcome)

        # Phase 3: Update quality history for trend detection
        current_score = self.get_quality_score()
        self.quality_history.append(current_score)

    def has_sufficient_data(self, min_samples: int = 3) -> bool:
        """
        Check if quality monitor has sufficient data for meaningful scores.

        Args:
            min_samples: Minimum number of samples required (default: 3)

        Returns:
            True if operation window has enough samples
        """
        return len(self.operation_window) >= min_samples

    def get_quality_score(self) -> float:
        """
        Calculate quality score from rolling window.

        Phase 3: Optionally uses weighted recent history where recent
        operations are weighted more heavily than older ones.

        Returns:
            Quality score (0-100 scale)
        """
        if not self.operation_window:
            return 50.0  # Neutral starting score

        if not self.enable_weighted_history:
            # Original unweighted calculation
            return self._calculate_unweighted_score()
        else:
            # Phase 3: Weighted calculation (recent operations matter more)
            return self._calculate_weighted_score()

    def _calculate_unweighted_score(self) -> float:
        """Calculate quality score without weighting (legacy behavior)."""
        total_points = 0
        for outcome in self.operation_window:
            if outcome == "success":
                total_points += self.success_points
            elif outcome == "timeout":
                total_points -= self.timeout_penalty
            elif outcome == "error":
                total_points -= self.error_penalty

        # Normalize to 0-100 scale
        max_score = len(self.operation_window) * self.success_points
        min_score = -len(self.operation_window) * self.error_penalty

        normalized = ((total_points - min_score) / (max_score - min_score)) * 100
        return max(0.0, min(100.0, normalized))

    def _calculate_weighted_score(self) -> float:
        """
        Phase 3: Calculate quality score with weighted recent history.

        Recent 25% of operations are weighted by recent_weight_factor (default 2.0x).
        This makes the system more responsive to recent changes in quality.
        """
        total_weighted_points = 0.0
        total_weight = 0.0

        # Recent 25% gets higher weight
        recent_threshold = int(len(self.operation_window) * 0.75)

        for idx, outcome in enumerate(self.operation_window):
            # Determine weight (recent operations get higher weight)
            weight = self.recent_weight_factor if idx >= recent_threshold else 1.0

            # Calculate points
            if outcome == "success":
                points = self.success_points
            elif outcome == "timeout":
                points = -self.timeout_penalty
            elif outcome == "error":
                points = -self.error_penalty
            else:
                points = 0

            total_weighted_points += points * weight
            total_weight += weight

        # Normalize to 0-100 scale with weighted max/min
        # Use average weight for normalization
        avg_weight = total_weight / len(self.operation_window) if self.operation_window else 1.0
        max_score = len(self.operation_window) * self.success_points * avg_weight
        min_score = -len(self.operation_window) * self.error_penalty * avg_weight

        normalized = ((total_weighted_points - min_score) / (max_score - min_score)) * 100
        return max(0.0, min(100.0, normalized))
    
    def get_speed_multiplier(self) -> float:
        """
        Get recommended speed multiplier based on quality score.
        
        Returns:
            Speed multiplier (0.25 - 1.0)
        """
        score = self.get_quality_score()
        
        if score >= 95:
            return 1.0  # excellent - full speed
        elif score >= 80:
            return 0.9  # good
        elif score >= 60:
            return 0.7  # fair
        elif score >= 40:
            return 0.5  # poor
        else:
            return 0.25  # critical - very slow
            
    def get_quality_tier(self) -> str:
        """
        Get quality tier name based on score.

        Returns:
            Tier name: 'excellent', 'good', 'fair', 'poor', or 'critical'
        """
        score = self.get_quality_score()

        if score >= 95:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 60:
            return "fair"
        elif score >= 40:
            return "poor"
        else:
            return "critical"

    def get_quality_trend(self) -> str:
        """
        Phase 3: Detect quality trend from recent history.

        Analyzes last 10 quality scores to determine if quality is
        improving, stable, or degrading.

        Returns:
            Trend: 'improving', 'stable', or 'degrading'
        """
        if len(self.quality_history) < 5:
            return "stable"  # Not enough data for trend

        # Calculate slope using simple linear regression
        # Positive slope = improving, negative = degrading
        n = len(self.quality_history)
        x_values = list(range(n))
        y_values = list(self.quality_history)

        # Calculate means
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        # Calculate slope
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Classify trend based on slope
        # Thresholds: >2 points/step = improving, <-2 = degrading
        if slope > 2.0:
            return "improving"
        elif slope < -2.0:
            return "degrading"
        else:
            return "stable"

    def should_trigger_warning(self) -> bool:
        """
        Phase 3: Check if quality has crossed warning threshold.

        Triggers warning if quality is 'poor' or worse, and degrading.

        Returns:
            True if warning should be triggered
        """
        tier = self.get_quality_tier()
        trend = self.get_quality_trend()

        # Warn if quality is poor/critical AND degrading
        return tier in ("poor", "critical") and trend == "degrading"

    def should_trigger_critical(self) -> bool:
        """
        Phase 3: Check if quality has crossed critical threshold.

        Triggers critical alert if quality is 'critical' tier.

        Returns:
            True if critical alert should be triggered
        """
        return self.get_quality_tier() == "critical"

    def reset(self) -> None:
        """Clear the operation window (used when reconnecting)."""
        self.operation_window.clear()
        self.quality_history.clear()


class DeviceConnection:
    """
    Manages connection state and health monitoring for a single device.

    Health States:
    - unknown: Initial state, no health data yet
    - healthy: Device responding normally to queries
    - degraded: Some failures detected, but still attempting communication
    - dead: Multiple consecutive failures, device unresponsive

    The connection tracks both the physical connection (is_open) and logical
    health (is_healthy) to handle USB-powered instruments that can maintain
    UART connection even when powered OFF.
    """

    def __init__(
        self,
        driver: Optional[Any],
        clock: Clock,
        failure_threshold: int = 3,
        degraded_threshold: int = 1,
        enable_quality_monitoring: bool = True,
        quality_window_size: int = 20,
        quality_success_points: int = 5,
        quality_timeout_penalty: int = 10,
        quality_error_penalty: int = 15,
        transport_type: str = "serial"
    ):
        self.driver = driver
        self.clock = clock
        self.transport_type = transport_type  # Phase 2: Track transport type for limits

        # Connection state
        self.last_open_attempt: float = -1e9  # Initialize to far past for immediate first attempt
        self.last_ok: float = 0.0

        # Health monitoring
        self.health_status: HealthStatus = "unknown"
        self.last_successful_response: float = 0.0
        self.consecutive_failures: int = 0
        self.failure_threshold: int = failure_threshold  # Mark dead after N failures
        self.degraded_threshold: int = degraded_threshold  # Mark degraded after N failures

        # Quality monitoring (adaptive throttling)
        self.quality_monitor: Optional[ConnectionQualityMonitor] = None
        if enable_quality_monitoring:
            self.quality_monitor = ConnectionQualityMonitor(
                window_size=quality_window_size,
                success_points=quality_success_points,
                timeout_penalty=quality_timeout_penalty,
                error_penalty=quality_error_penalty
            )

    def is_open(self) -> bool:
        """Check if physical serial connection is open."""
        if not self.driver:
            return False
        t = getattr(self.driver, 't', None)
        return bool(getattr(t, 'is_open', False))

    def is_healthy(self) -> bool:
        """
        Check if device is responding to queries.

        Returns True if health status is 'healthy' or 'degraded'.
        Returns False if 'dead' or 'unknown'.
        """
        return self.health_status in ("healthy", "degraded")

    def is_alive(self) -> bool:
        """
        Check if device is both connected AND responsive.

        This is the key method to distinguish between:
        - USB connection open (physical)
        - Instrument powered on and responding (logical)

        Returns True only if both conditions are met.
        """
        return self.is_open() and self.is_healthy()

    def record_success(self):
        """
        Record successful query/response.

        Resets failure counter and marks device as healthy.
        """
        self.last_successful_response = self.clock.now()
        self.consecutive_failures = 0
        self.health_status = "healthy"
        
        # Update quality monitor
        if self.quality_monitor:
            self.quality_monitor.record_operation("success")

    def record_failure(self, is_timeout: bool = False):
        """
        Record failed query (timeout, error, empty response).

        Transitions through health states based on consecutive failures:
        - 1st failure: degraded
        - 3rd failure: dead
        
        Args:
            is_timeout: True if failure was due to timeout, False for error
        """
        self.consecutive_failures += 1

        if self.consecutive_failures >= self.failure_threshold:
            self.health_status = "dead"
        elif self.consecutive_failures >= self.degraded_threshold:
            self.health_status = "degraded"
            
        # Update quality monitor
        if self.quality_monitor:
            outcome = "timeout" if is_timeout else "error"
            self.quality_monitor.record_operation(outcome)

    def reset_health(self):
        """Reset health state to unknown (used when reconnecting)."""
        self.health_status = "unknown"
        self.consecutive_failures = 0
        self.last_successful_response = 0.0
        
        # Reset quality monitor
        if self.quality_monitor:
            self.quality_monitor.reset()

    def get_quality_score(self) -> float:
        """
        Get connection quality score (0-100).
        
        Returns:
            Quality score, or 50.0 if monitoring disabled
        """
        if self.quality_monitor:
            return self.quality_monitor.get_quality_score()
        return 50.0  # Neutral score if monitoring disabled
    
    def get_quality_multiplier(self) -> float:
        """
        Get recommended speed multiplier based on connection quality.
        
        Returns:
            Speed multiplier (0.25 - 1.0)
        """
        if self.quality_monitor:
            return self.quality_monitor.get_speed_multiplier()
        return 1.0  # Full speed if monitoring disabled
    
    def get_quality_tier(self) -> str:
        """
        Get quality tier name.
        
        Returns:
            Tier name: 'excellent', 'good', 'fair', 'poor', 'critical', or 'unknown'
        """
        if self.quality_monitor:
            return self.quality_monitor.get_quality_tier()
        return "unknown"

    def identify(self) -> Optional[str]:
        """
        Query device identification.

        Note: Caller should use record_success()/record_failure() to track health.
        """
        if not self.driver:
            return None
        if hasattr(self.driver, 'query_identify'):
            return self.driver.query_identify()
        return None

    def close(self):
        """Close the physical connection."""
        try:
            if self.driver:
                self.driver.close()
        except Exception:
            pass

    def can_attempt_open(self, interval: float) -> bool:
        """Check if enough time has passed since last connection attempt."""
        now = self.clock.now()
        return (now - self.last_open_attempt) >= interval

    def mark_attempt(self):
        """Mark that a connection attempt was made (for backoff logic)."""
        self.last_open_attempt = self.clock.now()

    def mark_ok(self):
        """Mark connection as OK (legacy, prefer record_success for health tracking)."""
        self.last_ok = self.clock.now()
