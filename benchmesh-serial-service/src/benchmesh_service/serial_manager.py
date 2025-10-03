import json
import os
import time
import threading
import logging
import importlib
import inspect
from typing import Dict, List, Any
import yaml
from .logger import setup_logger

logger = logging.getLogger(__name__)

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
    def __init__(self, config_source: Any):
        print("Initializing SerialManager with config:", config_source)
        self.logger = setup_logger()
        self.devices: List[Dict] = self._load_devices(config_source)
        self.connections: Dict[str, object] = {}
        self.keep_running = True
        self.last_open_attempt: Dict[str, float] = {}
        self.last_ok: Dict[str, float] = {}
        self.last_probe: Dict[str, float] = {}
        self.dev_locks: Dict[str, threading.RLock] = {d.get('id'): threading.RLock() for d in self.devices if d.get('id')}
        self.dev_threads: Dict[str, threading.Thread] = {}
        self.registry: Dict[str, Dict[str, Any]] = {d.get('id'): {} for d in self.devices if d.get('id')}
        self._last_registry_log: float = 0.0

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
            print("Establishing connections to devices...", device)
            try:
                self.reconnect(device)
            except Exception as e:
                self.logger.info(f"Failed to connect to {device.get('name', device.get('id'))} on {device.get('port')}: {e}")

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

    def _update_registry(self, dev_id: str, key: str, value: Any):
        if dev_id not in self.registry:
            self.registry[dev_id] = {}
        self.registry[dev_id][key] = value

    def monitor_connections(self):
        print("Starting connection monitor thread.")
        while self.keep_running:
            now = time.time()
            # iterate over configured devices to ensure we attempt reopens too
            for dev in self.devices:
                device_id = dev.get('id')
                if not device_id:
                    continue
                drv = self.connections.get(device_id)
                is_open = getattr(getattr(drv, 't', None), 'is_open', False) if drv else False

                if is_open:
                    # Poll device status every 2 seconds (legacy monitor path)
                    last_poll = self.last_probe.get(device_id, 0.0)
                    if now - last_poll >= 2.0:
                        try:
                            status = None
                            if hasattr(drv, 'poll_status'):
                                status = drv.poll_status(1)
                            else:
                                status = {}
                            self._update_registry(device_id, 'status', status)
                            self.last_ok[device_id] = now
                            self.last_probe[device_id] = now
                            logger.debug("Polled status for %s -> %s", device_id, status)
                        except Exception:
                            # any error -> mark disconnected and allow reconnect on schedule
                            try:
                                drv.close()
                            except Exception:
                                pass
                            self.connections[device_id] = None
                            self.last_probe[device_id] = now
                # If not open or marked None -> try to reconnect every 2 seconds
                if not is_open or self.connections.get(device_id) is None:
                    last_attempt = self.last_open_attempt.get(device_id, 0.0)
                    if now - last_attempt >= 2.0:
                        self.last_open_attempt[device_id] = now
                        self.reconnect(dev)

            # Periodically dump registry at DEBUG
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
                # Single-device status check and reconnect logic
                now = time.time()
                dev = next((d for d in self.devices if d.get('id') == dev_id), None)
                if not dev:
                    time.sleep(0.5)
                    continue
                drv = self.connections.get(dev_id)
                is_open = getattr(getattr(drv, 't', None), 'is_open', False) if drv else False
                if is_open:
                    # Poll device status every 2 seconds
                    last_poll = self.last_probe.get(dev_id, 0.0)
                    if now - last_poll >= 2.0:
                        try:
                            status = None
                            if hasattr(drv, 'poll_status'):
                                status = drv.poll_status(1)
                            else:
                                status = {}
                            self._update_registry(dev_id, 'status', status)
                            self.last_ok[dev_id] = now
                            self.last_probe[dev_id] = now
                            logger.debug("Polled status for %s -> %s", dev_id, status)
                        except Exception as e:
                            logger.warning("Status poll failed for %s: %s; marking disconnected", dev_id, e)
                            try:
                                drv.close()
                            except Exception:
                                pass
                            self.connections[dev_id] = None
                            self.last_probe[dev_id] = now
                if not is_open or self.connections.get(dev_id) is None:
                    last_attempt = self.last_open_attempt.get(dev_id, 0.0)
                    if now - last_attempt >= 2.0:
                        self.last_open_attempt[dev_id] = now
                        self.reconnect(dev)
            # Periodically dump registry at DEBUG (per-device)
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
            device_id = dev.get('id')
        else:
            device_id = device_or_id
            dev = next((d for d in self.devices if d.get('id') == device_id), None)

        if not dev or not device_id:
            return None

        lock = self.dev_locks.setdefault(device_id, threading.RLock())
        with lock:
            # Close existing driver if present
            try:
                old = self.connections.get(device_id)
                if old:
                    close = getattr(old, 'close', None)
                    if callable(close):
                        close()
            except Exception:
                pass

            # Create driver instance using manifest EOL settings and config serial params
            try:
                driver_key = dev['driver']
                cls = _load_driver_class(driver_key)
                manifest = _load_manifest(driver_key)
                models = manifest.get('models', {}) or {}
                conn = {}
                if isinstance(models, dict) and models:
                    model_key = dev.get('model')
                    if model_key and isinstance(models.get(model_key), dict):
                        conn = models[model_key].get('connection', {}) or {}
                    else:
                        # Fallback to the first model's connection if not specified
                        conn = next(iter(models.values())).get('connection', {}) or {}
                seol = conn.get('seol', '\r')
                reol = conn.get('reol', '\r')
                drv = cls(
                    dev['port'],
                    dev.get('baud', 115200),
                    serial_mode=dev.get('serial', '8N1'),
                    seol=seol,
                    reol=reol,
                )
                # If the resolved class is actually the transport (due to missing driver class), wrap into a simple adapter
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
                self.connections[device_id] = drv
                # Perform one-time identify on (re)connect
                try:
                    ident = self._try_identify(drv)
                    if ident:
                        self._update_registry(device_id, 'IDN', ident)
                        self.last_ok[device_id] = time.time()
                        self.last_probe[device_id] = self.last_ok[device_id]
                        logger.debug("Identify on (re)connect %s -> %s", device_id, ident)
                except Exception as e:
                    logger.warning("Identify on (re)connect failed for %s: %s", device_id, e)
                self.logger.info(f"(Re)connected to {dev['name']} on {dev['port']}")
                return drv
            except Exception as e:
                self.logger.error(f"Reconnection failed for {dev.get('name', device_id)}: {e}")
                self.connections[device_id] = None
                return None

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
