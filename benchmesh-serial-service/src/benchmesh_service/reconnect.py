from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ReconnectPolicy:
    identify_interval: float = 1.0
    reconnect_interval: float = 2.0
