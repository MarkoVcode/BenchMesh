import json
import os
import time
import threading
import logging
import importlib
import inspect
from typing import Dict, List, Any, Tuple
import yaml
from .logger import setup_logger
from .registry import DeviceRegistry
from .manifest_resolver import ManifestResolver
from .driver_factory import DriverFactory
from .clock import Clock
from .connection import DeviceConnection
from .poll_worker import DeviceWorker
from .reconnect import ReconnectPolicy
from .metrics import MetricsRecorder

logger = logging.getLogger(__name__)
IDENTIFY_INTERVAL = 1.0


MANIFEST_ALIASES = {
    'tenma_psu': 'tenma_72',
}


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def _load_manifest(driver_key: str) -> Dict:
    manifest_key = MANIFEST_ALIASES.get(driver_key, driver_key)
    # Prefer manifest colocated with driver package (new layout)
    pkg_dir = os.path.join(os.path.dirname(__file__), 'drivers', manifest_key)
    pkg_manifest = os.path.join(pkg_dir, 'manifest.json')
    if os.path.exists(pkg_manifest):
        with open(pkg_manifest, 'r') as f:
            return json.load(f)

    # Fallback to repository-root drivers directory (legacy layout)
    here = _repo_root()
    legacy_manifest = os.path.join(here, 'drivers', manifest_key, 'manifest.json')
    with open(legacy_manifest, 'r') as f:
        return json.load(f)




def _get_class_channel_counts(dev: dict) -> Dict[str, int]:
    """Return mapping of class -> channel count for a device from manifest."""
    out: Dict[str, int] = {}
    try:
        driver_key = dev.get("driver")
        manifest = _load_manifest(driver_key) if driver_key else None
        if not isinstance(manifest, dict):
            return out
        models = manifest.get("models") or {}
        model_key = dev.get("model")
        model_cfg = None
        if model_key and isinstance(models.get(model_key), dict):
            model_cfg = models.get(model_key)
        elif isinstance(models, dict) and models:
            model_cfg = next(iter(models.values()))
        if not isinstance(model_cfg, dict):
            return out
        inst_class_block = model_cfg.get("instrument_class") or {}
        for klass, cfg in (inst_class_block or {}).items():
            features = (cfg or {}).get("features") or {}
            try:
                ch = int(features.get("channels", 1) or 1)
            except Exception:
                ch = 1
            out[str(klass)] = max(1, ch)
            # Fallback: detect nested class blocks mistakenly placed under another class
            for subk, subcfg in (cfg or {}).items():
                if not isinstance(subcfg, dict):
                    continue
                if subk in ("features", "modes", "pooling", "polling"):
                    continue
                sub_features = (subcfg or {}).get("features") or {}
                if sub_features:
                    try:
                        sch = int(sub_features.get("channels", 1) or 1)
                    except Exception:
                        sch = 1
                    out[str(subk)] = max(1, sch)
        return out
    except Exception:
        return out


def _get_class_poll_intervals(dev: dict) -> Dict[str, float]:
    """Return mapping of class -> poll interval (seconds) for classes that declare a polling method.

    Only classes with a defined pooling/polling entry are included. This prevents polling
    classes that have no configured poll method.
    """
    out: Dict[str, float] = {}
    try:
        driver_key = dev.get("driver")
        manifest = _load_manifest(driver_key) if driver_key else None
        if not isinstance(manifest, dict):
            return out
        models = manifest.get("models") or {}
        model_key = dev.get("model")
        model_cfg = None
        if model_key and isinstance(models.get(model_key), dict):
            model_cfg = models.get(model_key)
        elif isinstance(models, dict) and models:
            model_cfg = next(iter(models.values()))
        if not isinstance(model_cfg, dict):
            return out
        inst_class_block = model_cfg.get("instrument_class") or {}
        for klass, cfg in (inst_class_block or {}).items():
            pooling = (cfg or {}).get("pooling") or (cfg or {}).get("polling") or []
            # Pick the first polling entry we can use for the top-level class
            iv = None
            for entry in pooling:
                try:
                    mname = entry.get("method")
                    if mname:
                        iv = float(entry.get("interval", 2.0))
                        break
                except Exception:
                    continue
            if iv is not None:
                out[str(klass)] = iv
            # Also detect nested class blocks and their pooling
            for subk, subcfg in (cfg or {}).items():
                if not isinstance(subcfg, dict) or subk in ("features", "modes", "pooling", "polling"):
                    continue
                sub_pool = (subcfg or {}).get("pooling") or (subcfg or {}).get("polling") or []
                sub_iv = None
                for entry in sub_pool:
                    try:
                        mname = entry.get("method")
                        if mname:
                            sub_iv = float(entry.get("interval", 2.0))
                            break
                    except Exception:
                        continue
                if sub_iv is not None:
                    out[str(subk)] = sub_iv
        return out
    except Exception:
        return out
def _load_driver_class(driver_key: str):
    """Load a driver class given its key.

    Supports both legacy flat modules (benchmesh_service.drivers.<driver_key>)
    and new layout with subpackages (benchmesh_service.drivers.<pkg>.<module>).
    The class is expected to be reachable from the imported module namespace,
    either defined there or re-exported by the package's __init__.py.
    """
    tried = []
    folder_key = MANIFEST_ALIASES.get(driver_key, driver_key)

    # Candidate import names in order of preference
    candidates = [
        f"benchmesh_service.drivers.{driver_key}",
        f"benchmesh_service.drivers.{folder_key}",
        f"benchmesh_service.drivers.{folder_key}.driver",
        # explicit known class module for tenma alias
        f"benchmesh_service.drivers.{folder_key}.driver" if folder_key == 'tenma_72' else None,
    ]
    candidates = [c for c in candidates if c]

    for mod_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            # Return first class exposed on the module namespace
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                # Accept classes defined in the module or its submodules
                if getattr(obj, "__module__", "").startswith(mod.__name__):
                    return obj
            # If no classes found yet but module imported, keep trying next candidate
            tried.append(mod_name)
        except Exception as e:
            tried.append(f"{mod_name} ({e.__class__.__name__}: {e})")
            continue

    # As a fallback, attempt direct file import for <folder_key>/<driver_key>.py or <folder_key>/<folder_key>.py
    base_dir = os.path.join(os.path.dirname(__file__), 'drivers', folder_key)
    for file_base in (driver_key, folder_key, 'driver'):
        file_path = os.path.join(base_dir, f"{file_base}.py")
        if os.path.exists(file_path):
            try:
                spec = importlib.util.spec_from_file_location(f"benchmesh_service.drivers.{folder_key}.{file_base}", file_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    for _, obj in inspect.getmembers(mod, inspect.isclass):
                        # Only accept classes defined in this module (exclude imported helpers)
                        if getattr(obj, "__module__", "").startswith(mod.__name__):
                            return obj
            except Exception as e:
                tried.append(f"file:{file_path} ({e.__class__.__name__}: {e})")
                continue

    raise ImportError(f"No driver class found for key '{driver_key}'. Tried: {tried}")


class SerialManager:
    def __init__(self, config_source: Any, *, resolver: ManifestResolver | None = None, driver_factory: DriverFactory | None = None, clock: Clock | None = None, metrics: MetricsRecorder | None = None, policy: ReconnectPolicy | None = None):
        print("Initializing SerialManager with config:", config_source)
        self.logger = setup_logger()
        self.devices: List[Dict] = self._load_devices(config_source)
        self.keep_running = True
        self.dev_locks: Dict[str, threading.RLock] = {d.get('id'): threading.RLock() for d in self.devices if d.get('id')}
        self.dev_threads: Dict[str, threading.Thread] = {}
        self.registry_obj = DeviceRegistry({d.get('id'): {} for d in self.devices if d.get('id')})
        self.registry = self.registry_obj.data
        self.resolver = resolver or ManifestResolver()
        self.driver_factory = driver_factory or DriverFactory()
        self.clock = clock or Clock()
        self.metrics = metrics or MetricsRecorder()
        self.policy = policy or ReconnectPolicy()
        # External compatibility: connections map dev_id -> driver (or None)
        self.connections: Dict[str, object] = {}
        # Internal: device connections and workers
        self.dev_conns: Dict[str, DeviceConnection] = {}
        self.workers: Dict[str, DeviceWorker] = {}
        self._last_registry_log: float = 0.0
        # Backwards-compat attributes for tests
        self.last_open_attempt: Dict[str, float] = {}
        self.last_ok: Dict[str, float] = {}
        self.last_probe: Dict[str, float] = {}
        self.dev_class_channels: Dict[str, Dict[str, int]] = {}
        self.dev_class_poll_interval: Dict[str, Dict[str, float]] = {}
        self.last_probe_class: Dict[str, Dict[str, float]] = {}

        self.establish_connections()

    def _load_devices(self, source: Any) -> List[Dict]:
        if isinstance(source, list):
            return source
        # treat as path
        cfg_path = source if isinstance(source, str) else os.path.join(_repo_root(), 'config.yaml')
        if not os.path.isabs(cfg_path):
            cfg_path = os.path.join(_repo_root(), cfg_path)
        with open(cfg_path, 'r') as f:
            cfg = yaml.safe_load(f)
        return cfg.get('devices', [])

    def establish_connections(self):
        print("Establishing connections to devices...")
        for device in self.devices:
            dev_id = device.get('id')
            if not dev_id:
                continue
            try:
                self._open_or_identify(device)
            except Exception as e:
                self.logger.info(f"Failed to connect to {device.get('name', dev_id)} on {device.get('port')}: {e}")


    def _make_driver(self, dev: dict):
        driver_key = dev['driver']
        cls = self.driver_factory.load_driver_class(driver_key)
        seol, reol = self.resolver.get_connection_eol(dev)
        return cls(
            dev['port'],
            dev.get('baud', 115200),
            serial_mode=dev.get('serial', '8N1'),
            seol=seol,
            reol=reol,
        )

    def _open_or_identify(self, dev: dict):
        dev_id = dev.get('id')
        if not dev_id:
            return None
        conn = self.dev_conns.get(dev_id)
        if not conn:
            conn = DeviceConnection(None, self.clock)
            self.dev_conns[dev_id] = conn
            self.connections[dev_id] = None
        now = self.clock.now()
        # Attempt open/reconnect
        if not conn.is_open() and conn.can_attempt_open(self.policy.reconnect_interval):
            conn.mark_attempt()
            self.metrics.inc_reconnect_attempt(dev_id)
            try:
                drv = self._make_driver(dev)
                from .transport import SerialTransport
                if isinstance(drv, SerialTransport):
                    class _Adapter:
                        def __init__(self, t):
                            self.t = t
                        def close(self):
                            self.t.close()
                        def identify(self):
                            self.t.write_line('*IDN?')
                            return self.t.read_until_reol(1024)
                    drv = _Adapter(drv)
                conn.driver = drv
                self.connections[dev_id] = drv
                # If we had a worker, update its driver reference
                if dev_id in self.workers:
                    self.workers[dev_id].driver = drv
                self.metrics.inc_reconnect_success(dev_id)
            except Exception:
                conn.driver = None
                # Ensure registry reflects disconnected state
                self._clear_disconnected_registry(dev_id)
                return None
        # Ensure a worker exists even if not identified yet; it will be IDN-gated
        if dev_id not in self.workers:
            probe_map = getattr(self, 'last_probe_class', {}).setdefault(dev_id, {})
            self.workers[dev_id] = DeviceWorker(dev, conn.driver, self.registry_obj, self.resolver, self.metrics, probe_map)
        # Identify-only cadence
        if conn.is_open() and (not self.registry.get(dev_id, {}).get('IDN')) and conn.can_attempt_open(self.policy.identify_interval):
            conn.mark_attempt()
            try:
                ident = conn.identify()
                if ident:
                    self.registry_obj.set_idn(dev_id, ident)
                    self.metrics.inc_identify_success(dev_id)
                    conn.mark_ok()
                else:
                    self.metrics.inc_identify_fail(dev_id)
            except Exception:
                self.metrics.inc_identify_fail(dev_id)
        return conn.driver

    def _try_identify(self, drv):
        try:
            if hasattr(drv, 'identify'):
                return drv.identify()
            t = getattr(drv, 't', None)
            if t:
                t.write_line('*IDN?')
                return t.read_until_reol(256)
        except Exception as e:
            logger.warning("Identify failed: %s", e)
            raise
        return None

    def _update_registry(self, dev_id: str, key: str, value: Any, klass: str | None = None):
        self.registry_obj.update(dev_id, key, value, klass)

    def remove_registry_item(self, dev_id: str, key: str | None = None, prefix: bool = False, klass: str | None = None):
        self.registry_obj.remove_item(dev_id, key, prefix, klass)

    def clear_device_registry(self, dev_id: str):
        self.registry_obj.clear_device(dev_id)

    def _clear_disconnected_registry(self, dev_id: str):
        self.registry_obj.clear_disconnected(dev_id)

    def monitor_connections(self):
        print("Starting connection monitor thread.")
        while self.keep_running:
            now = time.time()
            for dev in self.devices:
                dev_id = dev.get('id')
                if not dev_id:
                    continue
                # Open or identify if needed; this will set up workers when IDN is available
                self._open_or_identify(dev)
                # Run worker tick if exists
                w = self.workers.get(dev_id)
                if w:
                    # Inject latest test overrides if present
                    w.interval_override = self.dev_class_poll_interval.get(dev_id) or None
                    if dev_id in self.last_probe_class:
                        w.last_probe_class = self.last_probe_class[dev_id]
                    try:
                        w.run_once(now)
                    except RuntimeError as e:
                        if str(e) == 'poll_empty':
                            # Drop connection and rely on reconnect cadence
                            self.connections[dev_id] = None
                            if dev_id in self.dev_conns:
                                self.dev_conns[dev_id].driver = None
                        else:
                            raise
            if now - self._last_registry_log >= 5.0:
                self._last_registry_log = now
                try:
                    logger.debug("Registry snapshot: %s", json.dumps(self.registry, ensure_ascii=False))
                except Exception:
                    logger.debug("Registry snapshot (repr): %r", self.registry)

    def _device_worker(self, dev_id: str):
        while self.keep_running:
            lock = self.dev_locks.get(dev_id)
            if not lock:
                time.sleep(0.5)
                continue
            with lock:
                now = time.time()
                dev = next((d for d in self.devices if d.get('id') == dev_id), None)
                if not dev:
                    time.sleep(0.5)
                    continue
                # Back-compat windowed reconnect attempt uses reconnect() for test spy
                if self.connections.get(dev_id) is None:
                    last_attempt = self.last_open_attempt.get(dev_id, 0.0)
                    if now - last_attempt >= 0.5:
                        self.last_open_attempt[dev_id] = now
                        try:
                            self.reconnect(dev_id)
                        except Exception:
                            pass
                else:
                    # Normal path: open/identify and then run worker
                    self._open_or_identify(dev)
                w = self.workers.get(dev_id)
                if w:
                    # Inject latest test overrides if present
                    w.interval_override = self.dev_class_poll_interval.get(dev_id) or None
                    if dev_id in self.last_probe_class:
                        w.last_probe_class = self.last_probe_class[dev_id]
                    try:
                        w.run_once(now)
                    except RuntimeError as e:
                        if str(e) == 'poll_empty':
                            # Drop connection and rely on reconnect cadence
                            self.connections[dev_id] = None
                            if dev_id in self.dev_conns:
                                self.dev_conns[dev_id].driver = None
                        else:
                            raise
            if time.time() - self._last_registry_log >= 5.0:
                self._last_registry_log = time.time()
                try:
                    logger.debug("Registry snapshot: %s", json.dumps(self.registry, ensure_ascii=False))
                except Exception:
                    logger.debug("Registry snapshot (repr): %r", self.registry)
            time.sleep(0.5)

    def reconnect(self, device_or_id):
        if isinstance(device_or_id, dict):
            dev = device_or_id
        else:
            dev = next((d for d in self.devices if d.get('id') == device_or_id), None)
        if not dev:
            return None
        return self._open_or_identify(dev)

    def start(self):
        self.establish_connections()
        # Start one worker thread per device for concurrent monitoring
        for dev in self.devices:
            dev_id = dev.get('id')
            if not dev_id:
                continue
            if dev_id in self.dev_threads and self.dev_threads[dev_id].is_alive():
                continue
            t = threading.Thread(target=self._device_worker, args=(dev_id,), name=f"dev-worker-{dev_id}", daemon=True)
            self.dev_threads[dev_id] = t
            t.start()
        # Keep legacy monitor if needed for any global duties (optional). Can be disabled if redundant.
        # threading.Thread(target=self.monitor_connections, daemon=True).start()

    def stop(self):
        self.keep_running = False
        # Join worker threads
        for dev_id, t in list(self.dev_threads.items()):
            try:
                t.join(timeout=1.0)
            except Exception:
                pass
        for drv in self.connections.values():
            try:
                drv.close()
            except Exception:
                pass
        self.logger.info("All connections closed.")

    def close_connections(self):
        for dev_id, drv in list(self.connections.items()):
            if drv:
                try:
                    drv.close()
                    logger.info("Closed connection %s", dev_id)
                except Exception:
                    logger.exception("Error closing %s", dev_id)
            self.connections[dev_id] = None

    def check_status(self):
        print("Checking status.")
        now = time.time()
        for dev in self.devices:
            dev_id = dev.get('id')
            if not dev_id:
                continue
            drv = self.connections.get(dev_id)
            if drv is None:
                last_attempt = self.last_open_attempt.get(dev_id, 0.0)
                if now - last_attempt >= 2.0:
                    self.last_open_attempt[dev_id] = now
                    new_drv = self.reconnect(dev)
                    if new_drv:
                        print("Opened connection to", dev_id)
                        self.connections[dev_id] = new_drv
                        self.last_ok[dev_id] = 0.0
                continue

            try:
                ident = None
                if hasattr(drv, 'identify'):
                    ident = drv.identify()
                else:
                    # fallback: try to access transport
                    t = getattr(drv, 't', None)
                    if t:
                        t.write_line('*IDN?')
                        ident = t.read_until_reol(256)

                if ident:
                    self.last_ok[dev_id] = now
                    self._update_registry(dev_id, 'IDN', ident)
                    logger.debug("Probe OK %s -> %s", dev_id, ident)
                else:
                    logger.debug("No response from %s on probe", dev_id)

            except Exception as e:
                logger.warning("Connection error for %s: %s", dev_id, e)
                try:
                    drv.close()
                except Exception:
                    pass
                self.connections[dev_id] = None
