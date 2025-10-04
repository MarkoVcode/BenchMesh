from __future__ import annotations
import time

class Clock:
    def now(self) -> float:
        return time.time()

class ManualClock(Clock):
    def __init__(self, start: float = 0.0):
        self._t = start
    def now(self) -> float:
        return self._t
    def advance(self, dt: float):
        self._t += dt
