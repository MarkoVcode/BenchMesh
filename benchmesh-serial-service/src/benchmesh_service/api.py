import os
import json
import asyncio
import subprocess
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from .serial_manager import SerialManager, _load_manifest
from .config import load_config
from .settings import settings

app = FastAPI(title="BenchMesh Serial Service", version="0.1.0")
API_PORT = int(os.getenv('API_PORT', '57666'))
UI_DEV_PORT = int(os.getenv('UI_PORT', '52893'))

# Enable CORS for development (Vite on :52892)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_manager: SerialManager | None = None
_valid_classes: set[str] | None = None
_frontend_proc: subprocess.Popen | None = None


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


@app.on_event("startup")
def on_startup():
    global _manager
    _manager = _make_manager()
    _manager.start()
    _load_valid_classes()
    _mount_static_ui_if_built(app)
    _start_frontend_dev_if_available()


@app.on_event("shutdown")
def on_shutdown():
    global _manager, _frontend_proc
    if _manager:
        _manager.stop()
        _manager = None
    if _frontend_proc:
        try:
            _frontend_proc.terminate()
        except Exception:
            pass
        _frontend_proc = None


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

@app.get("/instruments", summary="List instruments and last IDN", response_model=list)
def list_instruments():
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
                    })
        if classes_list:
            entry['classes'] = classes_list

        items.append(entry)
    return items


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
    if not hasattr(drv, method) or not callable(getattr(drv, method)):
        raise HTTPException(status_code=400, detail="Unknown or non-callable driver method")

    # Execute under device lock to avoid races with polling
    lock = _manager.dev_locks.get(device_id) if _manager else None
    import inspect
    ch = int(channel)
    func = getattr(drv, method)
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
    if not hasattr(drv, method) or not callable(getattr(drv, method)):
        raise HTTPException(status_code=400, detail="Unknown or non-callable driver method")

    import inspect
    arg = _coerce_arg(param)
    ch = int(channel)
    func = getattr(drv, method)

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
