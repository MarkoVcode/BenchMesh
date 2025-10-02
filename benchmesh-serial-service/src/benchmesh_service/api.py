import os
import json
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Response
from .serial_manager import SerialManager, _load_manifest
from .config import load_config

app = FastAPI(title="BenchMesh Serial Service", version="0.1.0")

_manager: SerialManager | None = None
_valid_classes: set[str] | None = None


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


@app.on_event("shutdown")
def on_shutdown():
    global _manager
    if _manager:
        _manager.stop()
        _manager = None


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
                for klass, klass_cfg in inst_class_block.items():
                    features = (klass_cfg or {}).get('features') or {}
                    channels = int(features.get('channels', 1) or 1)
                    # Build channel paths
                    ch_paths = [f"/instruments/{klass}/{dev_id}/{i+1}" for i in range(max(1, channels))]
                    classes_list.append({
                        "class": klass,
                        "channels": ch_paths,
                    })
        if classes_list:
            entry['classes'] = classes_list

        items.append(entry)
    return items


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
    try:
        if lock:
            with lock:
                value = getattr(drv, method)()
        else:
            value = getattr(drv, method)()
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

    arg = _coerce_arg(param)

    lock = _manager.dev_locks.get(device_id) if _manager else None
    try:
        if lock:
            with lock:
                getattr(drv, method)(arg)
        else:
            getattr(drv, method)(arg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Driver method execution failed: {e}")
    return Response(status_code=204)
