import os
import sys
import json
import asyncio
import subprocess
import hashlib
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, JSONResponse
from .serial_manager import SerialManager, _load_manifest
from .manifest_resolver import ManifestResolver
from .config import load_config, save_config
from .settings import settings
from .api_recording import create_recording_router
import benchmesh_service.services.recording_service as recording_service_module
import serial.tools.list_ports

API_PORT = int(os.getenv('API_PORT', '57666'))
UI_DEV_PORT = int(os.getenv('UI_PORT', '52893'))

_manager: SerialManager | None = None
_valid_classes: set[str] | None = None
_frontend_proc: subprocess.Popen | None = None
_manifest_resolver: ManifestResolver | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _manager, _manifest_resolver
    _manager = _make_manager()
    _manager.start()
    _manifest_resolver = ManifestResolver()
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


# SPA routing: Serve index.html for frontend routes (must be defined BEFORE mount)
from fastapi.responses import FileResponse as _FileResponse
import os as _os

@app.get("/ui/docs")
@app.get("/ui/docs/")
async def serve_docs_page():
    """Serve docs page route for Electron help menu"""
    base_dir = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', 'frontend'))
    dist_dir = _os.path.join(base_dir, 'dist')
    index_path = _os.path.join(dist_dir, 'index.html')
    if _os.path.isfile(index_path):
        return _FileResponse(index_path)
    return {"error": "Frontend not built"}

@app.get("/ui/metrics")
@app.get("/ui/metrics/")
async def serve_metrics_page():
    """Serve metrics page route for Electron help menu"""
    base_dir = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', 'frontend'))
    dist_dir = _os.path.join(base_dir, 'dist')
    index_path = _os.path.join(dist_dir, 'index.html')
    if _os.path.isfile(index_path):
        return _FileResponse(index_path)
    return {"error": "Frontend not built"}


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

@app.get("/version", summary="Application version", response_model=dict)
def get_version():
    """
    Return application version information.
    Reads from version.json at the repository root.
    """
    version_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'version.json')
    try:
        with open(version_path, 'r') as f:
            import json
            return json.load(f)
    except Exception as e:
        return {"version": "unknown", "name": "BenchMesh", "description": "Lab Instrument Control System", "error": str(e)}

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
                # Skip drivers that are explicitly disabled
                if not manifest.get('enabled', True):
                    continue
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
            # Filter out DEFAULT - it's an internal template, not a selectable model
            return [k for k in models.keys() if k != 'DEFAULT']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read manifest: {str(e)}")

@app.get("/serial-ports", summary="List available serial ports", response_model=list)
def list_serial_ports(exclude: str = ""):
    """
    List available serial ports on the system.

    Query parameters:
    - exclude: Comma-separated list of port paths to exclude (e.g., ports already in use)

    Returns a list of serial port information with:
    - device: Port path (e.g., /dev/ttyUSB0, COM3, /dev/cu.usbserial-1420)
    - description: Human-readable description of the device
    - manufacturer: Manufacturer name (if available)
    - serial_number: Device serial number (if available)
    - hwid: Hardware ID string

    Cross-platform support:
    - Windows: COM1, COM2, etc.
    - Linux: /dev/ttyUSB*, /dev/ttyACM*, etc. plus udev symlinks
    - macOS: /dev/cu.*, /dev/tty.*
    """
    try:
        # Get list of all available serial ports
        all_ports = serial.tools.list_ports.comports()

        # Parse exclude list
        excluded_ports = set()
        if exclude:
            excluded_ports = set(p.strip() for p in exclude.split(',') if p.strip())

        # Build result list
        result = []
        device_set = set()  # Track devices to avoid duplicates

        for port in all_ports:
            # Skip excluded ports
            if port.device in excluded_ports:
                continue

            result.append({
                "device": port.device,
                "description": port.description or "Unknown Device",
                "manufacturer": port.manufacturer or None,
                "serial_number": port.serial_number or None,
                "hwid": port.hwid or None
            })
            device_set.add(port.device)

        # On Linux, also discover udev symlinks to serial ports
        if sys.platform.startswith('linux'):
            try:
                dev_path = Path('/dev')
                if dev_path.exists():
                    for entry in dev_path.iterdir():
                        # Check if it's a symlink
                        if not entry.is_symlink():
                            continue

                        # Skip if already in our list or excluded
                        device_str = str(entry)
                        if device_str in device_set or device_str in excluded_ports:
                            continue

                        try:
                            # Resolve the symlink target
                            target = entry.resolve()
                            target_str = str(target)

                            # Check if target is a tty device
                            if target_str.startswith('/dev/tty'):
                                # Find the actual port info if available
                                manufacturer = None
                                serial_number = None
                                hwid = None

                                # Try to find the target in our port list
                                for port in all_ports:
                                    if port.device == target_str:
                                        manufacturer = port.manufacturer
                                        serial_number = port.serial_number
                                        hwid = port.hwid
                                        break

                                result.append({
                                    "device": device_str,
                                    "description": f"Symlink to {target.name}",
                                    "manufacturer": manufacturer,
                                    "serial_number": serial_number,
                                    "hwid": hwid
                                })
                                device_set.add(device_str)
                        except (OSError, RuntimeError):
                            # Skip broken symlinks or permission errors
                            continue
            except Exception as e:
                # Non-fatal - just log and continue with what we have
                print(f"Warning: Failed to scan /dev for symlinks: {e}")

        # Sort by device name for consistent ordering
        result.sort(key=lambda p: p["device"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list serial ports: {str(e)}")

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

    Changes are persisted to the config.yaml file.
    """
    global _manager

    if not isinstance(config, dict) or 'devices' not in config:
        raise HTTPException(status_code=400, detail="Config must contain 'devices' key")

    devices = config.get('devices', [])
    if not isinstance(devices, list):
        raise HTTPException(status_code=400, detail="'devices' must be a list")

    # Persist configuration to file before applying
    cfg_path = os.getenv("BENCHMESH_CONFIG", "config.yaml")
    try:
        save_config(cfg_path, devices)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save configuration to {cfg_path}: {str(e)}"
        )

    # Stop existing manager and all its threads
    if _manager:
        _manager.stop()

    # Create new manager with the new configuration
    _manager = SerialManager(devices)
    _manager.start()

    return {
        "status": "success",
        "message": f"Configuration updated with {len(devices)} device(s) and saved to {cfg_path}",
        "devices": _manager.devices
    }

def _build_instruments_list(class_filter: str | None = None) -> List[Dict[str, Any]]:
    """
    Build list of instruments with their classes and channels.
    
    Args:
        class_filter: Optional class code (e.g., 'PSU', 'DMM') to filter results.
                     If provided, only instruments with this class are included,
                     and only the matching classes are returned for each instrument.
    
    Returns:
        List of instrument dicts with id, optional IDN, and classes array
    """
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
        # Include name from config if available
        if 'name' in dev:
            entry['name'] = dev['name']
        reg_data = registry.get(dev_id, {})
        if 'IDN' in reg_data:
            entry['IDN'] = reg_data['IDN']

        # Add health status information
        conn = _manager.dev_conns.get(dev_id) if _manager else None
        if conn:
            entry['health'] = {
                'status': conn.health_status,
                'consecutive_failures': conn.consecutive_failures,
                'is_alive': conn.is_alive()
            }

        # Attempt to populate classes/channels from manifest based on device driver and model
        classes_list: List[Dict[str, Any]] = []
        if _manifest_resolver:
            try:
                driver_key = dev.get('driver')
                manifest = _load_manifest(driver_key) if driver_key else None
                if isinstance(manifest, dict):
                    # Use ManifestResolver to get merged model config (handles DEFAULT cascading)
                    model_cfg = _manifest_resolver._get_model_cfg(manifest, dev)
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
                            # Apply class filter if provided
                            if class_filter and klass != class_filter:
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
            except Exception:
                pass  # Fail gracefully, continue without classes
        
        # Only include instrument if it has matching classes (when filter is applied)
        if classes_list:
            entry['classes'] = classes_list
            items.append(entry)
        elif not class_filter:
            # Include instruments without classes only when no filter is applied
            items.append(entry)

    return items


@app.get("/instruments", summary="List instruments and last IDN", response_model=list)
def list_instruments(request: Request):
    items = _build_instruments_list()

    # Generate ETag from JSON content
    content = json.dumps(items, sort_keys=True)
    etag = f'"{hashlib.md5(content.encode()).hexdigest()}"'

    # Check If-None-Match header
    if_none_match = request.headers.get('if-none-match')
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})

    # Return response with ETag header
    return JSONResponse(content=items, headers={"ETag": etag})


@app.get("/instruments/{klass}", summary="List instruments filtered by class", response_model=list)
def list_instruments_by_class(klass: str, request: Request):
    """
    List instruments that have the specified instrument class.
    
    Returns only instruments with the specified class, and for each instrument
    only includes the matching class in the classes array.
    
    Args:
        klass: 3-letter instrument class code (e.g., 'PSU', 'DMM', 'ELL')
        
    Returns:
        List of instruments with the specified class, same structure as /instruments
        but filtered to only include matching classes
        
    Raises:
        404: If class is invalid or no instruments have this class
    """
    # Validate class code
    valid = _load_valid_classes()
    if klass not in valid:
        raise HTTPException(status_code=404, detail=f"Invalid instrument class: {klass}")
    
    # Build filtered instrument list
    items = _build_instruments_list(class_filter=klass)
    
    # Return 404 if no instruments match
    if not items:
        raise HTTPException(status_code=404, detail=f"No instruments found with class: {klass}")

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
    if not _manifest_resolver:
        raise HTTPException(status_code=500, detail="Manifest resolver not initialized")

    try:
        driver_key = dev.get('driver')
        manifest = _load_manifest(driver_key) if driver_key else None
    except Exception:
        manifest = None
    if not isinstance(manifest, dict):
        raise HTTPException(status_code=404, detail="Manifest not found for device")

    # Use ManifestResolver to get merged model config (handles DEFAULT cascading)
    model_cfg = _manifest_resolver._get_model_cfg(manifest, dev)
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


@app.get("/instruments/{klass}/{device_id}/methods", summary="List available methods for device with detailed metadata")
def list_available_methods(klass: str, device_id: str):
    """
    List all available methods for a device with rich metadata.
    
    Returns detailed information about each method including:
    - Method name (partial and full)
    - HTTP method (GET/POST)
    - Description
    - Parameters with types and requirements
    - Return type
    - Example usage
    
    This endpoint is designed for dynamic UI generation (e.g., Node-RED dropdowns)
    where method discovery needs to be programmatic.

    Example response:
    {
        "device_id": "psu-1",
        "class": "PSU",
        "methods": [
            {
                "name": "output_voltage",
                "full_name": "query_output_voltage",
                "http_method": "GET",
                "description": "Query the output voltage",
                "parameters": [
                    {
                        "name": "channel",
                        "type": "int",
                        "required": true,
                        "default": null,
                        "description": "Channel number"
                    }
                ],
                "returns": "string",
                "example": "GET /instruments/PSU/psu-1/1/output_voltage"
            }
        ]
    }
    """
    from .method_inspector import inspect_driver_methods, generate_example_url
    
    # Validate class
    valid = _load_valid_classes()
    if klass not in valid:
        raise HTTPException(status_code=404, detail="Invalid instrument class")
    
    # Get the driver
    driver = _get_driver_or_error(device_id)

    # Get manifest methods if available (for enrichment)
    manifest_methods = None
    global _manager, _manifest_resolver
    if _manager and _manifest_resolver:
        dev = next((d for d in _manager.devices if d.get('id') == device_id), None)
        if dev:
            try:
                from .serial_manager import _load_manifest
                driver_key = dev.get('driver')
                manifest = _load_manifest(driver_key) if driver_key else None
                if isinstance(manifest, dict):
                    # Get model-specific config
                    model_cfg = _manifest_resolver._get_model_cfg(manifest, dev)
                    if isinstance(model_cfg, dict):
                        manifest_methods = model_cfg.get('methods', {})
            except Exception:
                pass  # Fail gracefully, continue without manifest enrichment

    # Inspect driver methods
    methods = inspect_driver_methods(driver, manifest_methods)
    
    # Generate example URLs for each method
    for method in methods:
        if 'example' not in method:
            method['example'] = generate_example_url(method, klass, device_id)

    return {
        "device_id": device_id,
        "class": klass,
        "methods": methods
    }


@app.get("/ai/context", summary="Get AI assistant context", tags=["ai-assistant"])
@app.get("/ai/system-prompt", summary="Get AI assistant system prompt (alias)", tags=["ai-assistant"], include_in_schema=False)
async def get_ai_context(
    format: str = "markdown",
    include: str = "system,config,instruments,api,nodered,safety,examples"
):
    """
    Generate comprehensive AI assistant context based on current configuration.
    
    This endpoint provides a complete system prompt or structured data for AI assistants
    to understand and operate the BenchMesh system.
    
    **Included Information**:
    - System overview and architecture
    - Currently configured instruments with capabilities
    - Available API patterns and endpoints
    - Node-RED integration and custom nodes
    - Safety guidelines and constraints
    - Common task examples
    
    **Parameters**:
    - `format`: Output format ("markdown" for LLM consumption, "json" for structured data)
    - `include`: Comma-separated list of sections (default: all)
    
    **Use Cases**:
    - AI assistants operating instruments via natural language
    - Generating automation flows for Node-RED
    - Documentation and troubleshooting guidance
    - Training AI models on system capabilities
    
    **Example**:
    ```bash
    # Get full markdown context for Claude/GPT
    curl http://localhost:57666/ai/context
    
    # Get JSON structure
    curl "http://localhost:57666/ai/context?format=json"
    
    # Get only instruments and API sections
    curl "http://localhost:57666/ai/context?include=instruments,api"
    ```
    """
    from .ai_context_builder import AIContextBuilder
    
    global _manager, _manifest_resolver
    
    # Get version from version.json
    version = "0.1.0"
    try:
        version_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'version.json')
        with open(version_path, 'r') as f:
            version_data = json.load(f)
            version = version_data.get('version', version)
    except Exception:
        pass
    
    builder = AIContextBuilder(
        manager=_manager,
        manifest_resolver=_manifest_resolver,
        version=version
    )
    
    sections = [s.strip() for s in include.split(',') if s.strip()]
    context = await builder.build(sections=sections, format=format)
    
    if format == "markdown":
        return Response(content=context, media_type="text/markdown; charset=utf-8")
    else:
        return JSONResponse(content=context)


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


@app.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket):
    """WebSocket endpoint for broadcasting serial port utilization metrics."""
    await websocket.accept()
    try:
        while True:
            # Get metrics from manager's metrics collector
            metrics_summary = {}
            if _manager and hasattr(_manager, 'metrics_collector'):
                metrics_summary = _manager.metrics_collector.get_utilization_summary()

            await websocket.send_text(json.dumps(metrics_summary))
            await asyncio.sleep(30.0)  # Broadcast every 30 seconds
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

    ch = int(channel)

    # Determine arguments based on method signature
    import inspect
    func = getattr(drv, resolved_method)
    sig = inspect.signature(func)
    params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]

    # Build args tuple
    if len(params) >= 1:
        args = (ch,)
    else:
        args = ()

    # Execute via priority queue if unified polling enabled, otherwise use lock
    try:
        if _manager and _manager.unified_polling_enabled:
            # HIGH priority execution via queue
            value = _manager.enqueue_api_request(device_id, resolved_method, args=args)
        else:
            # Legacy: execute under device lock with metrics recording
            import time
            start_time = time.time()

            # Record operation start
            if _manager and hasattr(_manager, 'metrics_collector') and _manager.metrics_collector:
                _manager.metrics_collector.record_serial_operation_start(device_id, 'api')

            try:
                lock = _manager.dev_locks.get(device_id) if _manager else None
                if lock:
                    with lock:
                        if len(params) >= 1:
                            value = func(ch)
                        else:
                            value = func()
                else:
                    if len(params) >= 1:
                        value = func(ch)
                    else:
                        value = func()

                # Record successful API request with latency
                latency_ms = (time.time() - start_time) * 1000.0
                if _manager and hasattr(_manager, 'metrics_collector') and _manager.metrics_collector:
                    _manager.metrics_collector.record_api_request(device_id, resolved_method, latency_ms)
                    _manager.metrics_collector.record_serial_operation_end(device_id)
            except Exception as e:
                # Record operation end even on failure
                if _manager and hasattr(_manager, 'metrics_collector') and _manager.metrics_collector:
                    _manager.metrics_collector.record_serial_operation_end(device_id)
                raise e
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

    # Determine arguments based on method signature
    sig = inspect.signature(func)
    params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]

    # Build args tuple
    if len(params) >= 2:
        args = (ch, arg)
    elif len(params) == 1:
        args = (arg,)
    else:
        args = ()

    # Execute via priority queue if unified polling enabled, otherwise use lock
    try:
        if _manager and _manager.unified_polling_enabled:
            # HIGH priority execution via queue
            _manager.enqueue_api_request(device_id, resolved_method, args=args)
        else:
            # Legacy: execute under device lock with metrics recording
            import time
            start_time = time.time()

            # Record operation start
            if _manager and hasattr(_manager, 'metrics_collector') and _manager.metrics_collector:
                _manager.metrics_collector.record_serial_operation_start(device_id, 'api')

            try:
                lock = _manager.dev_locks.get(device_id) if _manager else None
                if lock:
                    with lock:
                        if len(params) >= 2:
                            func(ch, arg)
                        elif len(params) == 1:
                            func(arg)
                        else:
                            func()
                else:
                    if len(params) >= 2:
                        func(ch, arg)
                    elif len(params) == 1:
                        func(arg)
                    else:
                        func()

                # Record successful API request with latency
                latency_ms = (time.time() - start_time) * 1000.0
                if _manager and hasattr(_manager, 'metrics_collector') and _manager.metrics_collector:
                    _manager.metrics_collector.record_api_request(device_id, resolved_method, latency_ms)
                    _manager.metrics_collector.record_serial_operation_end(device_id)
            except Exception as e:
                # Record operation end even on failure
                if _manager and hasattr(_manager, 'metrics_collector') and _manager.metrics_collector:
                    _manager.metrics_collector.record_serial_operation_end(device_id)
                raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Driver method execution failed: {e}")
    return Response(status_code=204)
