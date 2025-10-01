import os
from fastapi import FastAPI
from .serial_manager import SerialManager
from .config import load_config

app = FastAPI(title="BenchMesh Serial Service", version="0.1.0")

_manager: SerialManager | None = None


def _make_manager() -> SerialManager:
    cfg_path = os.getenv("BENCHMESH_CONFIG", "config.yaml")
    cfg = load_config(cfg_path)
    return SerialManager(cfg.get('devices', []))


@app.on_event("startup")
def on_startup():
    global _manager
    _manager = _make_manager()
    _manager.start()


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
