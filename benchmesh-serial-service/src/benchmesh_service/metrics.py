from __future__ import annotations
from collections import defaultdict
from typing import Dict, Tuple

class MetricsRecorder:
    def __init__(self):
        self.reconnect_attempts: Dict[str, int] = defaultdict(int)
        self.reconnect_success: Dict[str, int] = defaultdict(int)
        self.identify_success: Dict[str, int] = defaultdict(int)
        self.identify_fail: Dict[str, int] = defaultdict(int)
        self.polls_total: Dict[Tuple[str,str], int] = defaultdict(int)  # (dev_id, class)
        self.polls_failed: Dict[Tuple[str,str], int] = defaultdict(int)

    def inc_reconnect_attempt(self, dev_id: str):
        self.reconnect_attempts[dev_id] += 1
    def inc_reconnect_success(self, dev_id: str):
        self.reconnect_success[dev_id] += 1
    def inc_identify_success(self, dev_id: str):
        self.identify_success[dev_id] += 1
    def inc_identify_fail(self, dev_id: str):
        self.identify_fail[dev_id] += 1
    def inc_poll_total(self, dev_id: str, klass: str):
        self.polls_total[(dev_id, klass)] += 1
    def inc_poll_failed(self, dev_id: str, klass: str):
        self.polls_failed[(dev_id, klass)] += 1
