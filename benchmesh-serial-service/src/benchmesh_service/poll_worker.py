from __future__ import annotations
from typing import Dict, Any
import logging
from .manifest_resolver import ManifestResolver
from .registry import DeviceRegistry

logger = logging.getLogger(__name__)

class DeviceWorker:
    """Run per-device polling cycles.

    Designed to be called periodically (or loop in a thread). For tests, run_once can be used.
    """
    def __init__(self, dev: dict, driver, registry: DeviceRegistry, resolver: ManifestResolver):
        self.dev = dev
        self.driver = driver
        self.registry = registry
        self.resolver = resolver
        self.last_probe_class: Dict[str, float] = {}

    def run_once(self, now: float):
        dev_id = self.dev.get('id')
        if not dev_id:
            return
        # IDN gating
        if not (self.registry.data.get(dev_id) or {}).get('IDN'):
            return
        class_channels = self.resolver.get_classes_and_channels(self.dev)
        poll_intervals = self.resolver.get_poll_intervals(self.dev)
        for klass, ch_count in (class_channels or {}).items():
            poll_iv = poll_intervals.get(klass, 2.0)
            last_poll = self.last_probe_class.get(klass, 0.0)
            if now - last_poll < poll_iv:
                continue
            polled_any = False
            meth_name = self.resolver.get_poll_method(self.dev, klass) or 'poll_status'
            meth = getattr(self.driver, meth_name, None)
            if not callable(meth):
                logger.warning("Poll method %s not implemented on driver %s; skipping class %s", meth_name, type(self.driver).__name__, klass)
                continue
            for ch in range(1, max(1, ch_count)+1):
                try:
                    st = meth(ch)
                except Exception as e:
                    logger.warning("Polling %s[%s] failed: %s", dev_id, klass, e)
                    st = {}
                if not st:
                    self.registry.clear_disconnected(dev_id)
                    polled_any = False
                    break
                key = f"status_ch{ch}"
                self.registry.update(dev_id, key, st, klass=klass)
                polled_any = True
            if polled_any:
                self.last_probe_class[klass] = now
