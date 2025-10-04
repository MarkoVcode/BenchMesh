from __future__ import annotations
import importlib
import inspect
from typing import Any, Type
from .manifest_resolver import MANIFEST_ALIASES

class DriverFactory:
    def __init__(self, base_pkg: str = 'benchmesh_service.drivers'):
        self.base_pkg = base_pkg

    def load_driver_class(self, driver_key: str) -> Type[Any]:
        folder_key = MANIFEST_ALIASES.get(driver_key, driver_key)
        candidates = [
            f"{self.base_pkg}.{driver_key}",
            f"{self.base_pkg}.{folder_key}",
            f"{self.base_pkg}.{folder_key}.driver",
        ]
        tried = []
        for mod_name in candidates:
            try:
                mod = importlib.import_module(mod_name)
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    if getattr(obj, '__module__', '').startswith(mod.__name__):
                        return obj
                tried.append(mod_name)
            except Exception as e:
                tried.append(f"{mod_name} ({e.__class__.__name__}: {e})")
                continue
        raise ImportError(f"Unable to locate driver class for {driver_key}; tried: {tried}")
