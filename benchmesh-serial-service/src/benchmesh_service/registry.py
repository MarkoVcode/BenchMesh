from __future__ import annotations
from typing import Any, Dict

class DeviceRegistry:
    def __init__(self, initial: Dict[str, Dict[str, Any]] | None = None):
        self.data: Dict[str, Dict[str, Any]] = initial or {}

    # Backward-compatible access to underlying dict
    def get(self, dev_id: str) -> Dict[str, Any]:
        if dev_id not in self.data:
            self.data[dev_id] = {}
        return self.data[dev_id]

    def set_idn(self, dev_id: str, ident: str):
        self.update(dev_id, 'IDN', ident)

    def update(self, dev_id: str, key: str, value: Any, klass: str | None = None):
        bucket = self.get(dev_id)
        if klass:
            cb = bucket.setdefault(klass, {})
            cb[key] = value
        else:
            bucket[key] = value

    def remove_item(self, dev_id: str, key: str | None = None, prefix: bool = False, klass: str | None = None):
        if dev_id not in self.data or not isinstance(self.data.get(dev_id), dict):
            self.data[dev_id] = {}
            return
        target = self.data[dev_id]
        if klass:
            target = target.setdefault(klass, {})
        if key is None:
            if klass:
                self.data[dev_id][klass] = {}
            else:
                self.data[dev_id] = {}
            return
        if prefix:
            for k in list(target.keys()):
                if isinstance(k, str) and k.startswith(key):
                    target.pop(k, None)
            return
        target.pop(key, None)

    def clear_device(self, dev_id: str):
        self.remove_item(dev_id, None)

    def clear_disconnected(self, dev_id: str):
        # Remove IDN and all per-class status entries when link drops
        self.remove_item(dev_id, 'IDN')
        # Clear status under all classes
        for klass in list((self.data.get(dev_id) or {}).keys()):
            # Class keys are short strings like PSU/DMM/AWG etc. Use known status prefix
            self.remove_item(dev_id, 'status_ch', prefix=True, klass=klass)
