import os
import json
import asyncio
import subprocess
import hashlib
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, JSONResponse
from .serial_manager import SerialManager, _load_manifest
from .config import load_config
from .settings import settings
from .api_recording import create_recording_router
import benchmesh_service.services.recording_service as recording_service_module

API_PORT = int(os.getenv('API_PORT', '57666'))
UI_DEV_PORT = int(os.getenv('UI_PORT', '52893'))

_manager: SerialManager | None = None
_valid_classes: set[str] | None = None
_frontend_proc: subprocess.Popen | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _manager
    _manager = _make_manager()
    _manager.start()
    _load_valid_classes()
    _mount_static_ui_if_built(app)
    _start_frontend_dev_if_available()

    # Initialize recording service with serial manager
    recording_service_module.recording_service = recording_service_module.RecordingService(serial_manager=_manager)

    yield

    # Shutdown
    global _frontend_proc
    if _manager:
        _manager.stop()
        _manager = None
    if _frontend_proc:
        try:
            _frontend_proc.terminate()
        except Exception:
            pass
        _frontend_proc = None


app = FastAPI(title="BenchMesh Serial Service", version="0.1.0", lifespan=lifespan)

# Enable CORS for development (Vite on :52892)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include recording API router
app.include_router(create_recording_router(), prefix="/recordings", tags=["recordings"])


def _make_manager() -> SerialManager:
    cfg_path = os.getenv("BENCHMESH_CONFIG", "config.yaml")
    cfg = load_config(cfg_path)
    return SerialManager(cfg.get('devices', []))


def _load_valid_classes() -> set[str]:
    global _valid_classes
    if _valid_classes is not None:
        return _valid_classes
    classes_path = os.path.join(os.path.dirname(__file__), 'drivers', 'classes.json')
    try:
        with open(classes_path, 'r') as f:
            data = json.load(f)
            classes = data.get('classes', {}) or {}
            _valid_classes = set(k for k in classes.keys() if isinstance(k, str) and len(k) == 3)
    except Exception:
        _valid_classes = set()
    return _valid_classes


def _start_frontend_dev_if_available():
    """
    Try to start the Vite dev server for the React UI. This is best-effort and will
    not crash the service if Node/npm are unavailable. Controlled by BENCHMESH_START_UI (default: '1').
    """
    global _frontend_proc
    if os.getenv('BENCHMESH_START_UI', '1') != '1':
        return
    # Expect the frontend at ../../frontend relative to this file
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
    pkg_json = os.path.join(base_dir, 'package.json')
    if not os.path.exists(pkg_json):
        return
    # Only launch if node_modules exists to avoid long install attempts
    node_modules = os.path.join(base_dir, 'node_modules')
    if not os.path.isdir(node_modules):
        return
    try:
        _frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"], cwd=base_dir,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        _frontend_proc = None


def _mount_static_ui_if_built(app: FastAPI):
    """If frontend has been built, mount it at /ui."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
    dist_dir = os.path.join(base_dir, 'dist')
    if os.path.isdir(dist_dir):
        app.mount("/ui", StaticFiles(directory=dist_dir, html=True), name="ui")

        # Add root redirect to UI
        @app.get("/")
        async def root_redirect():
            return RedirectResponse(url="/ui/")


def _coerce_arg(v: str) -> Any:
    s = v.strip()
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    try:
        if s.startswith("0") and s != "0":
            # preserve as string if leading zero (avoid octal confusion)
            raise ValueError
        return int(s)
    except Exception:
        pass
    try:
        return float(s)
    except Exception:
        return s


def _get_driver_or_error(device_id: str):
    global _manager
    if not _manager:
        raise HTTPException(status_code=400, detail="Service not initialized")
    drv = _manager.connections.get(device_id)
    if not drv:
        raise HTTPException(status_code=400, detail="Device not connected")
    return drv


def _resolve_method_name(driver: Any, partial_name: str, http_method: str) -> str:
    """
    Resolve partial method names to full driver method names based on HTTP verb.

    For GET requests: ONLY allows "query_{name}" pattern
    For POST requests: ONLY allows "set_{name}" pattern

    This security measure prevents arbitrary method execution on driver objects,
    including private methods or methods not intended for API exposure.

    Args:
        driver: The driver instance
        partial_name: The partial method name (e.g., "voltage", "current")
        http_method: The HTTP method ("GET" or "POST")

    Returns:
        The resolved method name that exists on the driver

    Raises:
        HTTPException: If no valid method is found
    """
    # Determine the required prefix based on HTTP method
    if http_method == "GET":
        prefixed = f"query_{partial_name}"
    elif http_method == "POST":
        prefixed = f"set_{partial_name}"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported HTTP method: {http_method}"
        )

    # Only allow the prefixed version - no arbitrary method calls
    if hasattr(driver, prefixed) and callable(getattr(driver, prefixed)):
        return prefixed

    # Method not found
    raise HTTPException(
        status_code=400,
        detail=f"Method '{prefixed}' not found on driver. " +
               f"Driver must implement {http_method.lower()} methods with appropriate prefix " +
               f"('query_' for GET, 'set_' for POST)"
    )


@app.get("/", include_in_schema=False)
def root():
    # If static UI is mounted, redirect there. Otherwise, assume dev server on 52893.
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
    dist_dir = os.path.join(base_dir, 'dist')
    if os.path.isdir(dist_dir):
        return RedirectResponse(url="/ui/")
    # Dev server convenience link
    host = os.getenv('UI_HOST', 'localhost')
    return RedirectResponse(url=f"http://{host}:{UI_DEV_PORT}")


@app.get("/status", summary="Service status", response_model=dict)
def get_status():
    global _manager
    if not _manager:
        return {"devices_total": 0, "connected": 0, "disconnected": 0}
    device_ids = [d.get('id') for d in _manager.devices if d.get('id')]
    total = len(device_ids)
    connected = sum(1 for did in device_ids if _manager.connections.get(did))
    return {"devices_total": total, "connected": connected, "disconnected": total - connected}

@app.get("/drivers", summary="List available drivers", response_model=dict)
def list_drivers():
    """
    Scan drivers folder and return available drivers with their vendor and family information.
    Returns a dict mapping driver_id (folder name) to {vendor, family} extracted from manifest.json
    """
    drivers = {}
    drivers_dir = os.path.join(os.path.dirname(__file__), 'drivers')

    if not os.path.isdir(drivers_dir):
        return drivers

    for entry in os.listdir(drivers_dir):
        entry_path = os.path.join(drivers_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        if entry.startswith('__') or entry.startswith('.'):
            continue

        manifest_path = os.path.join(entry_path, 'manifest.json')
        if not os.path.isfile(manifest_path):
            continue

        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                vendor = manifest.get('vendor', 'Unknown')
                family = manifest.get('family', 'Unknown')
                drivers[entry] = {
                    "vendor": vendor,
                    "family": family
                }
        except Exception:
            continue

    return drivers

@app.get("/drivers/{driver_id}", summary="List models for a specific driver", response_model=list)
def list_driver_models(driver_id: str):
    """
    Get list of supported models for a specific driver.
    Returns a list of model identifiers (keys from the manifest's models object).
    Example: ["72-2540", "72-2530"]
    """
    drivers_dir = os.path.join(os.path.dirname(__file__), 'drivers')
    manifest_path = os.path.join(drivers_dir, driver_id, 'manifest.json')

    if not os.path.isfile(manifest_path):
        raise HTTPException(status_code=404, detail=f"Driver '{driver_id}' not found")

    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            models = manifest.get('models', {})
            if not isinstance(models, dict):
                return []
            return list(models.keys())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read manifest: {str(e)}")

@app.get("/config", summary="Get current configuration from serial_manager")
def get_config():
    """Get the current runtime configuration from serial_manager.devices"""
    global _manager
    if not _manager:
        return {"devices": []}
    return {"devices": _manager.devices}

@app.post("/config", summary="Update configuration and restart connections")
def update_config(config: Dict[str, List[Dict]]):
    """
    Update the entire configuration and restart all connections.
    The payload must contain a 'devices' key with a list of device configs.
    This replaces the entire configuration - if you send 1 device, all others are removed.
    """
    global _manager

    if not isinstance(config, dict) or 'devices' not in config:
        raise HTTPException(status_code=400, detail="Config must contain 'devices' key")

    devices = config.get('devices', [])
    if not isinstance(devices, list):
        raise HTTPException(status_code=400, detail="'devices' must be a list")

    # Stop existing manager and all its threads
    if _manager:
        _manager.stop()

    # Create new manager with the new configuration
    _manager = SerialManager(devices)
    _manager.start()

    return {
        "status": "success",
        "message": f"Configuration updated with {len(devices)} device(s)",
        "devices": _manager.devices
    }

@app.get("/instruments", summary="List instruments and last IDN", response_model=list)
def list_instruments(request: Request):
    global _manager
    items = []
    if not _manager:
        return items

    registry = getattr(_manager, 'registry', {}) or {}
    for dev in _manager.devices:
        dev_id = dev.get('id')
        if not dev_id:
            continue
        entry: Dict[str, Any] = {"id": dev_id}
        reg_data = registry.get(dev_id, {})
        if 'IDN' in reg_data:
            entry['IDN'] = reg_data['IDN']

        # Attempt to populate classes/channels from manifest based on device driver and model
        try:
            driver_key = dev.get('driver')
            manifest = _load_manifest(driver_key) if driver_key else None
        except Exception:
            manifest = None
        classes_list: List[Dict[str, Any]] = []
        if isinstance(manifest, dict):
            models = manifest.get('models') or {}
            model_key = dev.get('model')
            model_cfg = None
            if model_key and isinstance(models.get(model_key), dict):
                model_cfg = models.get(model_key)
            elif isinstance(models, dict) and models:
                # fallback to first model entry
                model_cfg = next(iter(models.values()))
            if isinstance(model_cfg, dict):
                inst_class_block = model_cfg.get('instrument_class') or {}
                declared_classes = model_cfg.get('classes') or []
                # Union of keys present in instrument_class and declared classes list
                klass_keys = set(inst_class_block.keys()) | {c for c in declared_classes if isinstance(c, str)}
                valid = _load_valid_classes()
                for klass in sorted(klass_keys):
                    # Only include known 3-letter classes
                    if klass not in valid:
                        continue
                    klass_cfg = inst_class_block.get(klass) or {}
                    features = klass_cfg.get('features') or {}
                    try:
                        channels = int(features.get('channels', 1) or 1)
                    except Exception:
                        channels = 1
                    channels = max(1, channels)
                    # Build channel paths
                    ch_paths = [f"/instruments/{klass}/{dev_id}/{i+1}" for i in range(channels)]
                    classes_list.append({
                        "class": klass,
                        "channels": ch_paths,
                        "ui_component": klass_cfg.get('ui_component')
                    })
        if classes_list:
            entry['classes'] = classes_list

        items.append(entry)

    # Generate ETag from JSON content
    content = json.dumps(items, sort_keys=True)
    etag = f'"{hashlib.md5(content.encode()).hexdigest()}"'

    # Check If-None-Match header
    if_none_match = request.headers.get('if-none-match')
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})

    # Return response with ETag header
    return JSONResponse(content=items, headers={"ETag": etag})


@app.get("/instruments/{klass}/{device_id}", summary="Get manifest features for class on device", response_model=dict)
def get_manifest_features(klass: str, device_id: str):
    # Validate class and device id
    valid = _load_valid_classes()
    if klass not in valid:
        raise HTTPException(status_code=404, detail="Invalid instrument class")
    global _manager
    if not _manager or not any(d.get('id') == device_id for d in (_manager.devices if _manager else [])):
        raise HTTPException(status_code=404, detail="Unknown device id")

    # Locate device config
    dev = next((d for d in (_manager.devices or []) if d.get('id') == device_id), None)
    if not dev:
        raise HTTPException(status_code=404, detail="Unknown device id")

    # Load manifest for this device's driver and model
    try:
        driver_key = dev.get('driver')
        manifest = _load_manifest(driver_key) if driver_key else None
    except Exception:
        manifest = None
    if not isinstance(manifest, dict):
        raise HTTPException(status_code=404, detail="Manifest not found for device")

    models = manifest.get('models') or {}
    model_key = dev.get('model')
    model_cfg = None
    if model_key and isinstance(models.get(model_key), dict):
        model_cfg = models.get(model_key)
    elif isinstance(models, dict) and models:
        model_cfg = next(iter(models.values()))
    if not isinstance(model_cfg, dict):
        raise HTTPException(status_code=404, detail="Model configuration not found")

    iclasses = model_cfg.get('instrument_class') or {}
    cfg = iclasses.get(klass)
    if not isinstance(cfg, dict):
        # Search nested under other classes (e.g., DMM under PSU)
        for _, topcfg in (iclasses or {}).items():
            if isinstance(topcfg, dict) and isinstance(topcfg.get(klass), dict):
                cfg = topcfg.get(klass)
                break
    if not isinstance(cfg, dict):
        raise HTTPException(status_code=404, detail="Class configuration not found in manifest")

    features = cfg.get('features') or {}
    if not isinstance(features, dict):
        features = {}
    return features


@app.get("/instruments/{klass}/{device_id}/methods", summary="List available query methods for device")
def list_available_methods(klass: str, device_id: str):
    """
    List all available query methods for a device.
    Returns method names WITHOUT the 'query_' prefix (as used in recording API).

    Example response:
    {
        "device_id": "eol-1",
        "class_name": "ELL",
        "methods": ["volt", "curr", "pow", "status", ...]
    }
    """
    # Get the driver
    driver = _get_driver_or_error(device_id)

    # Get all methods that start with 'query_'
    query_methods = [
        method[6:]  # Remove 'query_' prefix
        for method in dir(driver)
        if method.startswith('query_') and callable(getattr(driver, method))
    ]

    return {
        "device_id": device_id,
        "class_name": klass,
        "methods": sorted(query_methods)
    }


@app.websocket("/ws/registry")
async def ws_registry(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            reg = getattr(_manager, 'registry', {}) if _manager else {}
            await websocket.send_text(json.dumps(reg))
            await asyncio.sleep(settings.ws_broadcast_interval)
    except WebSocketDisconnect:
        pass
    except Exception:
        # ignore other errors to avoid crashing the app
        pass



@app.get("/instruments/{klass}/{device_id}/{channel}/{method}", summary="Call driver method (read-only)")
def call_driver_get(klass: str, device_id: str, channel: str, method: str):
    # Validate class
    valid = _load_valid_classes()
    if klass not in valid:
        raise HTTPException(status_code=404, detail="Invalid instrument class")
    # Validate channel (1-9 only as a single digit)
    if not (isinstance(channel, str) and len(channel) == 1 and channel.isdigit() and channel != '0'):
        raise HTTPException(status_code=404, detail="Invalid channel")
    # Validate device id exists in config
    global _manager
    if not any(d.get('id') == device_id for d in (_manager.devices if _manager else [])):
        raise HTTPException(status_code=404, detail="Unknown device id")

    drv = _get_driver_or_error(device_id)

    # Resolve method name (e.g., "voltage" -> "query_voltage")
    resolved_method = _resolve_method_name(drv, method, "GET")

    # Execute under device lock to avoid races with polling
    lock = _manager.dev_locks.get(device_id) if _manager else None
    import inspect
    ch = int(channel)
    func = getattr(drv, resolved_method)
    try:
        if lock:
            with lock:
                sig = inspect.signature(func)
                params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
                # Bound method: signature excludes self
                if len(params) >= 1:
                    value = func(ch)
                else:
                    value = func()
        else:
            sig = inspect.signature(func)
            params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            if len(params) >= 1:
                value = func(ch)
            else:
                value = func()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Driver method execution failed: {e}")
    return {"path": f"/instruments/{klass}/{device_id}/{channel}/{method}", "value": value}


@app.post("/instruments/{klass}/{device_id}/{channel}/{method}/{param}", summary="Call driver method (write)")
def call_driver_post(klass: str, device_id: str, channel: str, method: str, param: str):
    # Validate class
    valid = _load_valid_classes()
    if klass not in valid:
        raise HTTPException(status_code=404, detail="Invalid instrument class")
    # Validate channel (1-9 only as a single digit)
    if not (isinstance(channel, str) and len(channel) == 1 and channel.isdigit() and channel != '0'):
        raise HTTPException(status_code=404, detail="Invalid channel")
    # Validate device id exists in config
    global _manager
    if not any(d.get('id') == device_id for d in (_manager.devices if _manager else [])):
        raise HTTPException(status_code=404, detail="Unknown device id")

    drv = _get_driver_or_error(device_id)

    # Resolve method name (e.g., "current" -> "set_current")
    resolved_method = _resolve_method_name(drv, method, "POST")

    import inspect
    arg = _coerce_arg(param)
    ch = int(channel)
    func = getattr(drv, resolved_method)

    lock = _manager.dev_locks.get(device_id) if _manager else None
    try:
        if lock:
            with lock:
                sig = inspect.signature(func)
                params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
                if len(params) >= 2:
                    func(ch, arg)
                elif len(params) == 1:
                    func(arg)
                else:
                    func()
        else:
            sig = inspect.signature(func)
            params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            if len(params) >= 2:
                func(ch, arg)
            elif len(params) == 1:
                func(arg)
            else:
                func()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Driver method execution failed: {e}")
    return Response(status_code=204)
