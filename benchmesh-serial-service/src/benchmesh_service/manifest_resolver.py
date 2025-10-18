from __future__ import annotations
import json
import os
from typing import Dict, Any, Optional

MANIFEST_ALIASES = {
    'tenma_psu': 'tenma_72',
}

class ManifestResolver:
    """Resolves manifest-sourced information for a given device config.

    Exposes:
    - get_classes_and_channels(dev)
    - get_poll_intervals(dev)
    - get_poll_method(dev, klass)
    - get_connection_eol(dev) -> (seol, reol)
    """

    def __init__(self, repo_root: Optional[str] = None, package_dir: Optional[str] = None):
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        self.package_dir = package_dir or os.path.join(os.path.dirname(__file__), 'drivers')

    def _load_manifest(self, driver_key: str) -> Dict[str, Any]:
        manifest_key = MANIFEST_ALIASES.get(driver_key, driver_key)
        pkg_manifest = os.path.join(self.package_dir, manifest_key, 'manifest.json')
        if os.path.exists(pkg_manifest):
            with open(pkg_manifest, 'r') as f:
                return json.load(f)
        legacy = os.path.join(self.repo_root, 'drivers', manifest_key, 'manifest.json')
        with open(legacy, 'r') as f:
            return json.load(f)

    def _get_model_cfg(self, manifest: Dict[str, Any], dev: dict) -> Dict[str, Any]:
        models = manifest.get('models') or {}
        model_key = dev.get('model')
        if model_key and isinstance(models.get(model_key), dict):
            return models.get(model_key) or {}
        if isinstance(models, dict) and models:
            return next(iter(models.values())) or {}
        return {}

    def get_classes_and_channels(self, dev: dict) -> Dict[str, int]:
        out: Dict[str, int] = {}
        driver_key = dev.get('driver')
        if not driver_key:
            return out
        manifest = self._load_manifest(driver_key)
        model_cfg = self._get_model_cfg(manifest, dev)
        inst = model_cfg.get('instrument_class') or {}
        for klass, cfg in (inst or {}).items():
            features = (cfg or {}).get('features') or {}
            ch = features.get('channels', 1) or 1
            try:
                ch = int(ch)
            except Exception:
                ch = 1
            out[str(klass)] = max(1, ch)
            # nested blocks support
            for subk, subcfg in (cfg or {}).items():
                if not isinstance(subcfg, dict) or subk in ('features','modes','pooling','polling'):
                    continue
                sub_features = (subcfg or {}).get('features') or {}
                if sub_features:
                    sch = sub_features.get('channels', 1) or 1
                    try:
                        sch = int(sch)
                    except Exception:
                        sch = 1
                    out[str(subk)] = max(1, sch)
        return out

    def get_poll_intervals(self, dev: dict) -> Dict[str, float]:
        out: Dict[str, float] = {}
        driver_key = dev.get('driver')
        if not driver_key:
            return out
        manifest = self._load_manifest(driver_key)
        model_cfg = self._get_model_cfg(manifest, dev)

        # Check model-level polling first (new unified approach)
        model_interval = self._first_poll_interval(model_cfg)

        inst = model_cfg.get('instrument_class') or {}
        for klass, cfg in (inst or {}).items():
            # Use model-level interval if available, otherwise class-level
            iv = model_interval if model_interval is not None else self._first_poll_interval(cfg)
            if iv is not None:
                out[str(klass)] = iv
            # nested
            for subk, subcfg in (cfg or {}).items():
                if not isinstance(subcfg, dict) or subk in ('features','modes','pooling','polling'):
                    continue
                siv = model_interval if model_interval is not None else self._first_poll_interval(subcfg)
                if siv is not None:
                    out[str(subk)] = siv
        return out

    def _first_poll_interval(self, cfg: Dict[str, Any]) -> Optional[float]:
        polling = (cfg or {}).get('pooling') or (cfg or {}).get('polling') or []
        for entry in polling:
            name = entry.get('method')
            if name:
                try:
                    return float(entry.get('interval', 2.0))
                except Exception:
                    return 2.0
        return None

    def get_poll_method(self, dev: dict, klass: str) -> Optional[str]:
        driver_key = dev.get('driver')
        if not driver_key:
            return None
        manifest = self._load_manifest(driver_key)
        model_cfg = self._get_model_cfg(manifest, dev)

        # Check model-level polling first (new unified approach)
        model_method = self._first_poll_method(model_cfg)
        if model_method:
            return model_method

        # Fall back to class-level polling (backward compatibility)
        iclasses = (model_cfg or {}).get('instrument_class', {}) or {}
        # top-level
        meth = self._first_poll_method(iclasses.get(klass, {}) or {})
        if meth:
            return meth
        # nested under some other class
        for _, topcfg in (iclasses or {}).items():
            if isinstance(topcfg, dict) and isinstance(topcfg.get(klass), dict):
                meth = self._first_poll_method(topcfg.get(klass) or {})
                if meth:
                    return meth
        return None

    def _first_poll_method(self, cfg: Dict[str, Any]) -> Optional[str]:
        polling = (cfg or {}).get('pooling') or (cfg or {}).get('polling') or []
        for entry in polling:
            name = entry.get('method')
            if name:
                return name
        return None

    def has_multi_class_polling(self, dev: dict) -> bool:
        """
        Check if device uses unified multi-class polling.
        
        Multi-class polling means one poll method returns data for all classes,
        avoiding multiple serial operations on a single port.
        
        Returns True if device manifest has device-level polling with multi_class flag.
        """
        driver_key = dev.get('driver')
        if not driver_key:
            return False
        
        try:
            manifest = self._load_manifest(driver_key)
            model_cfg = self._get_model_cfg(manifest, dev)
            
            # Check for device-level polling (outside instrument_class)
            polling = model_cfg.get('pooling') or model_cfg.get('polling') or []
            for entry in polling:
                if entry.get('multi_class'):
                    return True
            
            return False
        except Exception:
            return False
    
    def get_multi_class_poll_config(self, dev: dict) -> Optional[Dict[str, Any]]:
        """
        Get device-level polling configuration for multi-class devices.
        
        Returns dict with 'method' and 'interval' if multi-class polling is configured,
        None otherwise.
        """
        driver_key = dev.get('driver')
        if not driver_key:
            return None
        
        try:
            manifest = self._load_manifest(driver_key)
            model_cfg = self._get_model_cfg(manifest, dev)
            
            # Check for device-level polling (outside instrument_class)
            polling = model_cfg.get('pooling') or model_cfg.get('polling') or []
            for entry in polling:
                if entry.get('multi_class'):
                    return {
                        'method': entry.get('method', 'poll_status'),
                        'interval': float(entry.get('interval', 2.0))
                    }
            
            return None
        except Exception:
            return None

    def get_connection_eol(self, dev: dict) -> tuple[str, str]:
        driver_key = dev.get('driver')
        if not driver_key:
            return ('\r','\r')
        manifest = self._load_manifest(driver_key)
        model_cfg = self._get_model_cfg(manifest, dev)
        conn = (model_cfg or {}).get('connection') or {}
        seol = conn.get('seol', '\r')
        reol = conn.get('reol', '\r')
        return (seol, reol)
