from __future__ import annotations
from typing import Optional, Any, Literal
from .clock import Clock

# Health status states for device connection
HealthStatus = Literal["unknown", "healthy", "degraded", "dead"]


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
        degraded_threshold: int = 1
    ):
        self.driver = driver
        self.clock = clock

        # Connection state
        self.last_open_attempt: float = -1e9  # Initialize to far past for immediate first attempt
        self.last_ok: float = 0.0

        # Health monitoring
        self.health_status: HealthStatus = "unknown"
        self.last_successful_response: float = 0.0
        self.consecutive_failures: int = 0
        self.failure_threshold: int = failure_threshold  # Mark dead after N failures
        self.degraded_threshold: int = degraded_threshold  # Mark degraded after N failures

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

    def record_failure(self):
        """
        Record failed query (timeout, error, empty response).

        Transitions through health states based on consecutive failures:
        - 1st failure: degraded
        - 3rd failure: dead
        """
        self.consecutive_failures += 1

        if self.consecutive_failures >= self.failure_threshold:
            self.health_status = "dead"
        elif self.consecutive_failures >= self.degraded_threshold:
            self.health_status = "degraded"

    def reset_health(self):
        """Reset health state to unknown (used when reconnecting)."""
        self.health_status = "unknown"
        self.consecutive_failures = 0
        self.last_successful_response = 0.0

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
