from __future__ import annotations
from typing import Optional, Any
from .clock import Clock

class DeviceConnection:
    def __init__(self, driver: Optional[Any], clock: Clock):
        self.driver = driver
        self.clock = clock
        # Initialize to a far past time so initial open/identify attempts are allowed immediately
        self.last_open_attempt: float = -1e9
        self.last_ok: float = 0.0

    def is_open(self) -> bool:
        if not self.driver:
            return False
        t = getattr(self.driver, 't', None)
        return bool(getattr(t, 'is_open', False))

    def identify(self) -> Optional[str]:
        if not self.driver:
            return None
        if hasattr(self.driver, 'query_identify'):
            return self.driver.query_identify()
        return None

    def close(self):
        try:
            if self.driver:
                self.driver.close()
        except Exception:
            pass

    def can_attempt_open(self, interval: float) -> bool:
        now = self.clock.now()
        return (now - self.last_open_attempt) >= interval

    def mark_attempt(self):
        self.last_open_attempt = self.clock.now()

    def mark_ok(self):
        self.last_ok = self.clock.now()
