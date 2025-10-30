import os
import sys
import json
import time
import asyncio
import subprocess
import hashlib
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect, Request, Query, Path, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, JSONResponse
from .serial_manager import SerialManager, _load_manifest
from .manifest_resolver import ManifestResolver
from .config import load_config, save_config
from .settings import settings
from .api_recording import create_recording_router
import benchmesh_service.services.recording_service as recording_service_module
import serial.tools.list_ports
from .transport import discover_usbtmc_devices
from .models import (
    StatusResponse,
    VersionResponse,
    DriversResponse,
    SerialPortInfo,
    USBTMCDeviceInfo,
    ConfigResponse,
    ConfigUpdateResponse,
    ConfigUpdate,
    InstrumentInfo,
    ManifestFeaturesResponse,
    MethodsResponse,
    MetricsSummary,
    InstrumentQueryResponse,
)

logger = logging.getLogger(__name__)

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


app = FastAPI(
    title="BenchMesh Serial Service",
    version="0.1.0",
    description="""
BenchMesh is a consistent, browser-based cockpit for lab instruments.

## Features

* **Multi-device support** - Connect and control multiple instruments simultaneously
* **WebSocket streaming** - Real-time data updates via WebSocket
* **Data recording** - Record multi-device data with pause/resume support
* **AI integration** - AI-powered automation and assistance
* **Modular drivers** - Extensible driver architecture

## Authentication

Currently no authentication is required (local development).
    """,
    openapi_tags=[
        {
            "name": "system",
            "description": "System status, version information, and OpenAPI specifications"
        },
        {
            "name": "configuration",
            "description": "Device configuration, driver discovery, and port scanning"
        },
        {
            "name": "instruments",
            "description": "Instrument listing, capabilities, and method discovery"
        },
        {
            "name": "instrument-control",
            "description": "Direct instrument control operations (query and set methods)"
        },
        {
            "name": "monitoring",
            "description": "Performance metrics, health monitoring, and throttling statistics"
        },
        {
            "name": "recordings",
            "description": "Data recording, export, and playback"
        },
        {
            "name": "ai-assistant",
            "description": "AI assistant context generation and integration"
        },
        {
            "name": "websockets",
            "description": "Real-time data streaming via WebSocket connections"
        }
    ],
    lifespan=lifespan
)

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


@app.get(
    "/status",
    tags=["system"],
    response_model=StatusResponse,
    summary="Get service status",
    responses={
        200: {
            "description": "Service status with device connection counts",
            "content": {
                "application/json": {
                    "example": {
                        "devices_total": 3,
                        "connected": 2,
                        "disconnected": 1
                    }
                }
            }
        }
    }
)
def get_status():
    """
    Get current service status and device connection statistics.

    Returns the total number of configured devices and how many are currently
    connected vs disconnected. Useful for health monitoring and dashboards.

    **Connection States:**
    - **connected**: Device driver is active and responding
    - **disconnected**: Device driver failed to connect or connection lost
    """
    global _manager
    if not _manager:
        return StatusResponse(devices_total=0, connected=0, disconnected=0)
    device_ids = [d.get('id') for d in _manager.devices if d.get('id')]
    total = len(device_ids)
    connected = sum(1 for did in device_ids if _manager.connections.get(did))
    return StatusResponse(
        devices_total=total,
        connected=connected,
        disconnected=total - connected
    )

@app.get(
    "/version",
    tags=["system"],
    response_model=VersionResponse,
    summary="Get application version",
    responses={
        200: {
            "description": "Application version information",
            "content": {
                "application/json": {
                    "example": {
                        "version": "0.1.0",
                        "name": "BenchMesh",
                        "description": "Lab Instrument Control System"
                    }
                }
            }
        }
    }
)
def get_version():
    """
    Get application version information.

    Returns version number, application name, and description.
    Reads from version.json at the repository root.

    **Version Format**: Semantic versioning (MAJOR.MINOR.PATCH)
    """
    version_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'version.json')
    try:
        with open(version_path, 'r') as f:
            import json
            data = json.load(f)
            return VersionResponse(**data)
    except Exception as e:
        return VersionResponse(
            version="unknown",
            name="BenchMesh",
            description="Lab Instrument Control System",
            error=str(e)
        )

@app.get(
    "/openapi.json",
    tags=["system"],
    summary="Get OpenAPI specification (JSON)",
    include_in_schema=False,
    response_class=FileResponse
)
async def get_openapi_json():
    """
    Serve pre-generated OpenAPI specification in JSON format.

    This endpoint serves the OpenAPI 3.0 specification that was generated
    during the build process. The spec includes all API endpoints, request/response
    models, and documentation.

    **Generation**: Run `./start.sh --uibuild` to regenerate the spec.

    **Use Cases:**
    - Import into API testing tools (Postman, Insomnia)
    - Generate API clients in various languages
    - API documentation and exploration
    """
    spec_path = os.path.join(
        os.path.dirname(__file__),
        'static',
        'openapi',
        'openapi.json'
    )
    if not os.path.exists(spec_path):
        raise HTTPException(
            status_code=404,
            detail="OpenAPI spec not generated. Run build with --uibuild flag to generate."
        )
    return FileResponse(
        spec_path,
        media_type="application/json",
        filename="benchmesh-openapi.json"
    )

@app.get(
    "/openapi.yaml",
    tags=["system"],
    summary="Get OpenAPI specification (YAML)",
    include_in_schema=False,
    response_class=FileResponse
)
async def get_openapi_yaml():
    """
    Serve pre-generated OpenAPI specification in YAML format.

    This endpoint serves the OpenAPI 3.0 specification that was generated
    during the build process. YAML format is often preferred for human readability.

    **Generation**: Run `./start.sh --uibuild` to regenerate the spec.

    **Use Cases:**
    - Human-readable API documentation
    - Version control and diff-friendly format
    - Import into OpenAPI tools that prefer YAML
    """
    spec_path = os.path.join(
        os.path.dirname(__file__),
        'static',
        'openapi',
        'openapi.yaml'
    )
    if not os.path.exists(spec_path):
        raise HTTPException(
            status_code=404,
            detail="OpenAPI spec not generated. Run build with --uibuild flag to generate."
        )
    return FileResponse(
        spec_path,
        media_type="application/x-yaml",
        filename="benchmesh-openapi.yaml"
    )

@app.get(
    "/drivers",
    tags=["configuration"],
    response_model=DriversResponse,
    summary="List available instrument drivers",
    responses={
        200: {
            "description": "Dictionary of available drivers with vendor, family, and transport information",
            "content": {
                "application/json": {
                    "example": {
                        "tenma_72": {
                            "vendor": "TENMA",
                            "family": "72-SERIES",
                            "supported_transports": ["serial"]
                        },
                        "owon_spm": {
                            "vendor": "OWON",
                            "family": "SPM",
                            "supported_transports": ["serial", "usbtmc"]
                        },
                        "rigol_dho": {
                            "vendor": "RIGOL",
                            "family": "DHO",
                            "supported_transports": ["usbtmc"]
                        }
                    }
                }
            }
        }
    }
)
def list_drivers():
    """
    List all available instrument drivers in the system.

    Scans the drivers directory and returns information about each enabled driver.
    Each driver ID maps to vendor name, product family, and supported transport types.

    **Driver Discovery:**
    - Only enabled drivers with valid manifest.json files are returned
    - Drivers can be disabled by setting `"enabled": false` in their manifest
    - Each driver folder must contain a manifest.json with vendor/family info

    **Supported Transports:**
    - `serial`: RS232/USB-Serial communication
    - `usbtmc`: USB Test & Measurement Class (IEEE 488.2 over USB)
    - `tcpip`: Network/Ethernet communication (future)

    **Use Cases:**
    - Populate driver selection dropdowns in configuration UI
    - Discover which instruments can be controlled
    - Check transport compatibility before device configuration
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
                supported_transports = manifest.get('supported_transports', ['serial'])  # Default to serial
                drivers[entry] = {
                    "vendor": vendor,
                    "family": family,
                    "supported_transports": supported_transports
                }
        except Exception:
            continue

    return drivers

@app.get(
    "/metrics",
    tags=["monitoring"],
    response_model=MetricsSummary,
    summary="Get metrics for all devices"
)
def get_all_metrics():
    """
    Phase 4: Get performance and adaptive throttling metrics for all devices.

    Returns metrics including:
    - Serial port utilization %
    - QPS (queries per second)
    - API latency percentiles (P95, P99)
    - Average queue depth
    - Throttle events and skip rate
    - Backoff multipliers
    - Connection quality scores, tiers, and trends
    - Transport types
    """
    global _manager
    if not _manager or not _manager.metrics_collector:
        return {"error": "Metrics collector not available"}

    summary = _manager.metrics_collector.get_utilization_summary()
    return MetricsSummary(
        summary=summary,
        timestamp=time.time()
    )

@app.get(
    "/metrics/{device_id}",
    tags=["monitoring"],
    response_model=dict,
    summary="Get metrics for specific device"
)
def get_device_metrics(
    device_id: str = Path(..., description="Device identifier")
):
    """
    Phase 4: Get performance and adaptive throttling metrics for a specific device.

    Returns detailed metrics for the specified device including utilization,
    latency, queue depth, throttling events, backoff state, and quality metrics.
    """
    global _manager
    if not _manager or not _manager.metrics_collector:
        return {"error": "Metrics collector not available"}

    metrics = _manager.metrics_collector.get_device_metrics(device_id)
    if not metrics:
        return {"error": f"No metrics available for device {device_id}"}

    metrics["timestamp"] = time.time()
    return metrics

@app.get(
    "/drivers/{driver_id}",
    tags=["configuration"],
    response_model=List[str],
    summary="List models for specific driver",
    responses={
        200: {
            "description": "List of supported model identifiers",
            "content": {
                "application/json": {
                    "example": ["72-2540", "72-2530", "72-2535"]
                }
            }
        },
        404: {"description": "Driver not found"}
    }
)
def list_driver_models(
    driver_id: str = Path(..., description="Driver identifier", example="tenma_72")
):
    """
    Get list of supported models for a specific driver.

    Returns model identifiers from the driver's manifest.
    The DEFAULT template model is excluded as it's not user-selectable.

    **Example**: `tenma_72` returns `["72-2540", "72-2530"]`
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

@app.get(
    "/serial-ports",
    tags=["configuration"],
    response_model=List[SerialPortInfo],
    summary="List available serial ports",
    responses={
        200: {"description": "List of available serial ports with device information"},
        500: {"description": "Failed to scan serial ports"}
    }
)
def list_serial_ports(
    exclude: str = Query(
        "",
        description="Comma-separated list of port paths to exclude",
        example="/dev/ttyUSB0,/dev/ttyUSB1"
    )
):
    """
    List available serial ports on the system.

    Scans all available serial ports and returns detailed information including
    device path, description, manufacturer, serial number, and hardware ID.

    **Cross-platform Support:**
    - **Windows**: COM1, COM2, etc.
    - **Linux**: /dev/ttyUSB*, /dev/ttyACM*, plus udev symlinks
    - **macOS**: /dev/cu.*, /dev/tty.*

    **Excluding Ports**: Use the `exclude` parameter to filter out ports already
    in use or not relevant for selection.
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
                logger.warning(f"Failed to scan /dev for symlinks: {e}")

        # Sort by device name for consistent ordering
        result.sort(key=lambda p: p["device"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list serial ports: {str(e)}")

@app.get(
    "/usbtmc-devices",
    tags=["configuration"],
    response_model=List[USBTMCDeviceInfo],
    summary="List available USB TMC devices",
    responses={
        200: {"description": "List of available USB TMC devices"},
        500: {"description": "Failed to scan USB TMC devices"}
    }
)
def list_usbtmc_devices(
    exclude: str = Query(
        "",
        description="Comma-separated list of device paths to exclude",
        example="/dev/usbtmc0,/dev/tmcDGE2070"
    )
):
    """
    List available USB Test & Measurement Class (TMC) devices.

    USB TMC is a standard protocol for test and measurement instruments
    over USB. Devices appear as /dev/usbtmc* on Linux with proper kernel support.

    **Returned Information:**
    - Device path (e.g., `/dev/usbtmc0`)
    - USB vendor/product IDs
    - Manufacturer and product names
    - Serial numbers (if available)

    **Excluding Devices**: Use the `exclude` parameter to filter out devices
    already in use.
    """
    try:
        # Get list of all available USB TMC devices
        all_devices = discover_usbtmc_devices()

        # Parse exclude list
        excluded_devices = set()
        if exclude:
            excluded_devices = set(d.strip() for d in exclude.split(',') if d.strip())

        # Filter out excluded devices
        result = [dev for dev in all_devices if dev['device'] not in excluded_devices]

        # Sort by device name for consistent ordering
        result.sort(key=lambda d: d["device"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list USB TMC devices: {str(e)}")

@app.get(
    "/config",
    tags=["configuration"],
    response_model=ConfigResponse,
    summary="Get current configuration"
)
def get_config():
    """
    Get the current runtime configuration.

    Returns the active device configuration from the SerialManager.
    This reflects the currently running configuration, which may differ
    from the config file if modifications haven't been persisted.
    """
    global _manager
    if not _manager:
        return ConfigResponse(devices=[])
    return ConfigResponse(devices=_manager.devices)

@app.post(
    "/config",
    tags=["configuration"],
    response_model=ConfigUpdateResponse,
    summary="Update configuration",
    responses={
        200: {"description": "Configuration updated successfully"},
        400: {"description": "Invalid configuration format or validation error"},
        500: {"description": "Failed to save configuration to disk"}
    }
)
def update_config(config: ConfigUpdate = Body(...)):
    """
    Update the entire device configuration and restart all connections.

    **⚠️ Warning**: This replaces the entire configuration. If you send 1 device,
    all others will be removed.

    **Process:**
    1. Validates the new configuration using Pydantic models
    2. Persists changes to config.yaml file
    3. Stops all existing device connections
    4. Creates new SerialManager with updated config
    5. Starts new device connections

    **Configuration Persistence**: Changes are saved to the config file specified
    by the `BENCHMESH_CONFIG` environment variable (default: `~/.benchmesh/config.yaml`).
    """
    global _manager

    devices = [dev.model_dump() for dev in config.devices]

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

    return ConfigUpdateResponse(
        status="success",
        message=f"Configuration updated with {len(devices)} device(s) and saved to {cfg_path}",
        devices=_manager.devices
    )

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


@app.get(
    "/instruments",
    tags=["instruments"],
    response_model=List[InstrumentInfo],
    summary="List all configured instruments",
    responses={
        200: {
            "description": "List of all instruments with their classes, channels, and health status",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "psu-1",
                            "name": "TENMA PSU",
                            "IDN": "TENMA,72-2540,SN12345,V1.0",
                            "health": {
                                "status": "healthy",
                                "consecutive_failures": 0,
                                "is_alive": True
                            },
                            "classes": [
                                {
                                    "class": "PSU",
                                    "channels": [
                                        "/instruments/PSU/psu-1/1",
                                        "/instruments/PSU/psu-1/2",
                                        "/instruments/PSU/psu-1/3"
                                    ],
                                    "ui_component": "psu_control"
                                }
                            ]
                        }
                    ]
                }
            }
        },
        304: {"description": "Not modified (content matches ETag)"}
    }
)
def list_instruments(
    request: Request,
    if_none_match: Optional[str] = Header(None, description="ETag for conditional requests (e.g., '\"abc123\"')")
):
    """
    Get a complete list of all configured instruments with their capabilities.

    Returns comprehensive information for each instrument including:
    - Device ID and display name
    - Identification string from *IDN? SCPI command
    - Health status and connection state
    - Available instrument classes (PSU, DMM, SPM, etc.)
    - Channel endpoints for each class
    - UI component recommendations

    **ETag Support:**
    This endpoint supports conditional requests via ETags for efficient polling.
    Include the `If-None-Match` header with the previous ETag to receive 304 Not Modified
    when content hasn't changed.

    **Health Status:**
    - `healthy`: No recent failures, fully operational
    - `degraded`: Some failures but still attempting communication
    - `unhealthy`: Consecutive failures exceed threshold

    **Use Cases:**
    - Build instrument dashboards and navigation
    - Monitor device connection status
    - Discover available instrument capabilities
    - Generate dynamic UI based on connected devices
    """
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


@app.get(
    "/instruments/{klass}",
    tags=["instruments"],
    response_model=List[InstrumentInfo],
    summary="List instruments filtered by class",
    responses={
        200: {
            "description": "List of instruments that support the specified class",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "psu-1",
                            "name": "TENMA PSU",
                            "IDN": "TENMA,72-2540,SN12345,V1.0",
                            "health": {"status": "healthy", "consecutive_failures": 0, "is_alive": True},
                            "classes": [
                                {
                                    "class": "PSU",
                                    "channels": ["/instruments/PSU/psu-1/1", "/instruments/PSU/psu-1/2", "/instruments/PSU/psu-1/3"],
                                    "ui_component": "psu_control"
                                }
                            ]
                        }
                    ]
                }
            }
        },
        304: {"description": "Not modified (content matches ETag)"},
        404: {"description": "Invalid instrument class code"}
    }
)
def list_instruments_by_class(
    klass: str = Path(..., description="3-letter instrument class code (e.g., PSU, DMM, SPM, OSC)", example="PSU", regex="^[A-Z]{3}$"),
    request: Request = None,
    if_none_match: Optional[str] = Header(None, description="ETag for conditional requests")
):
    """
    Filter instruments by instrument class type.

    Returns only instruments that support the specified class. For each instrument,
    only the matching class information is included (other classes are filtered out).

    **Common Class Codes:**
    - `PSU`: Power Supply Unit - voltage/current source control
    - `DMM`: Digital Multimeter - voltage/current/resistance measurement
    - `SPM`: Switching Power Module - electronic load/source mode
    - `OSC`: Oscilloscope - waveform capture and analysis
    - `FGN`: Function Generator - waveform generation
    - `OEL`: DC Electronic Load - current sink control

    **ETag Support:**
    Supports conditional requests via ETags. Include `If-None-Match` header to avoid
    redundant transfers when the instrument list hasn't changed.

    **Use Cases:**
    - Build UI pages specific to one instrument type (e.g., "All Power Supplies")
    - Filter devices by capability for automation tasks
    - Discover available channels for a specific instrument class

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


@app.get(
    "/instruments/{klass}/{device_id}",
    tags=["instruments"],
    response_model=ManifestFeaturesResponse,
    summary="Get instrument class features",
    responses={
        200: {
            "description": "Features dictionary for the specified class and device",
            "content": {
                "application/json": {
                    "example": {
                        "channels": 3,
                        "voltage_range": {"min": 0, "max": 30},
                        "current_range": {"min": 0, "max": 5},
                        "voltage_resolution": 0.01,
                        "current_resolution": 0.001
                    }
                }
            }
        },
        404: {"description": "Invalid class code, unknown device, or class not supported by device"}
    }
)
def get_manifest_features(
    klass: str = Path(..., description="3-letter instrument class code", example="PSU"),
    device_id: str = Path(..., description="Unique device identifier from configuration", example="psu-1")
):
    """
    Get the feature specifications for a specific instrument class on a device.

    Returns the features dictionary from the driver's manifest for the specified
    instrument class. This provides metadata about capabilities, ranges, and limits.

    **Typical Features:**
    - `channels`: Number of available channels (integer)
    - `voltage_range`: Min/max voltage (dict with min/max keys)
    - `current_range`: Min/max current
    - `*_resolution`: Measurement or control resolution
    - `*_accuracy`: Accuracy specifications
    - Device-specific capabilities and limits

    **Use Cases:**
    - Validate user inputs before sending commands
    - Display capability ranges in UI controls
    - Generate appropriate control widgets (e.g., sliders with correct ranges)
    - Check if device supports specific features before using them

    **Note:** Features are defined in the driver's manifest.json file and vary by
    instrument type and model.
    """
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


@app.get(
    "/instruments/{klass}/{device_id}/methods",
    tags=["instruments"],
    response_model=MethodsResponse,
    summary="List available methods"
)
def list_available_methods(
    klass: str = Path(..., description="Instrument class code"),
    device_id: str = Path(..., description="Device identifier")
):
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
    """
    WebSocket endpoint for real-time device registry updates.

    Broadcasts the current device registry every 200ms (configurable via BM_WS_INTERVAL).
    The registry contains IDN strings and polled status for all connected devices.

    **Message Format:**
    ```json
    {
        "psu-1": {
            "IDN": "TENMA,72-2540,SN12345,V1.0",
            "status": {
                "channel_1_voltage": "12.503V",
                "channel_1_current": "0.523A",
                "channel_1_output": "ON"
            }
        },
        "dmm-1": {
            "IDN": "OWON,XDM1041,SN98765,V1.2",
            "status": {
                "measurement": "5.123V"
            }
        }
    }
    ```

    **Update Frequency:** Every 200ms by default (5 updates/second)

    **Use Cases:**
    - Real-time instrument dashboards
    - Live measurement displays
    - Connection status monitoring
    - Status change notifications

    **Client Example:**
    ```javascript
    const ws = new WebSocket('ws://localhost:57666/ws/registry');
    ws.onmessage = (event) => {
        const registry = JSON.parse(event.data);
        console.log('Device status:', registry);
    };
    ```
    """
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
    """
    WebSocket endpoint for real-time performance metrics streaming.

    Broadcasts comprehensive performance and health metrics for all devices every 30 seconds.
    Includes serial port utilization, API latency, queue depth, throttling stats, and quality scores.

    **Message Format:**
    ```json
    {
        "psu-1": {
            "device_id": "psu-1",
            "utilization_pct": 45.2,
            "qps": 12.5,
            "api_latency_p95_ms": 125.3,
            "api_latency_p99_ms": 180.7,
            "avg_queue_depth": 2.3,
            "throttle_events": 0,
            "skip_rate_pct": 0.0,
            "backoff_multiplier": 1.0,
            "quality_score": 0.95,
            "quality_tier": "excellent",
            "quality_trend": "stable",
            "transport_type": "serial"
        }
    }
    ```

    **Metrics Included:**
    - `utilization_pct`: Serial port utilization (0-100%)
    - `qps`: Queries per second throughput
    - `api_latency_p95_ms`: 95th percentile API latency
    - `api_latency_p99_ms`: 99th percentile API latency
    - `avg_queue_depth`: Average command queue depth
    - `throttle_events`: Count of throttling events
    - `quality_score`: Connection quality (0.0-1.0)
    - `quality_tier`: excellent/good/fair/poor
    - `quality_trend`: improving/stable/degrading

    **Update Frequency:** Every 30 seconds

    **Use Cases:**
    - Real-time performance monitoring dashboards
    - Connection quality tracking
    - Throttling and queue depth visualization
    - Performance degradation alerts
    - Capacity planning and optimization

    **Client Example:**
    ```javascript
    const ws = new WebSocket('ws://localhost:57666/ws/metrics');
    ws.onmessage = (event) => {
        const metrics = JSON.parse(event.data);
        Object.entries(metrics).forEach(([deviceId, stats]) => {
            console.log(`${deviceId}: ${stats.utilization_pct}% utilization, quality: ${stats.quality_tier}`);
        });
    };
    ```

    **See Also:** `GET /metrics` for one-time metrics retrieval
    """
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



@app.get(
    "/instruments/{klass}/{device_id}/{channel}/{method}",
    tags=["instrument-control"],
    response_model=InstrumentQueryResponse,
    summary="Query instrument measurement or status",
    responses={
        200: {
            "description": "Successfully queried instrument, returns measured value",
            "content": {
                "application/json": {
                    "examples": {
                        "voltage": {
                            "summary": "Query PSU output voltage",
                            "value": {
                                "path": "/instruments/PSU/psu-1/1/output_voltage",
                                "value": "12.503V"
                            }
                        },
                        "current": {
                            "summary": "Query DMM current measurement",
                            "value": {
                                "path": "/instruments/DMM/dmm-1/1/current",
                                "value": "0.523A"
                            }
                        },
                        "status": {
                            "summary": "Query PSU output status",
                            "value": {
                                "path": "/instruments/PSU/psu-1/2/output_status",
                                "value": "ON"
                            }
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid parameters or method execution failed"},
        404: {"description": "Invalid class, unknown device, or method not found"}
    }
)
def call_driver_get(
    klass: str = Path(..., description="3-letter instrument class code", example="PSU"),
    device_id: str = Path(..., description="Unique device identifier from configuration", example="psu-1"),
    channel: str = Path(..., regex="^[1-9]$", description="Channel number (1-9)", example="1"),
    method: str = Path(..., description="Method name without 'query_' prefix (e.g., 'voltage', 'current')", example="output_voltage")
):
    """
    Query a measurement or status from an instrument channel.

    This is the primary endpoint for reading values from instruments. The method name
    is automatically prefixed with `query_` and resolved to the driver method.

    **Method Resolution:**
    - Partial name `voltage` → resolves to `query_voltage()` driver method
    - Partial name `current` → resolves to `query_current()` driver method
    - Only methods with `query_` prefix can be called via GET (security feature)

    **Common Query Methods:**
    - `output_voltage`: Read actual output voltage
    - `output_current`: Read actual output current
    - `set_voltage`: Read voltage setpoint
    - `set_current`: Read current setpoint
    - `output_status`: Check if output is enabled (ON/OFF)
    - `mode`: Read operating mode (e.g., CV/CC for PSU, CURR/VOLT for SPM)

    **Priority Queue Execution:**
    When unified polling is enabled, API requests are queued with HIGH priority,
    ensuring they execute ahead of background polling for minimal latency.

    **Example Requests:**
    ```bash
    # Query PSU channel 1 output voltage
    GET /instruments/PSU/psu-1/1/output_voltage

    # Query DMM channel 1 current measurement
    GET /instruments/DMM/dmm-1/1/current

    # Query electronic load mode on channel 2
    GET /instruments/OEL/load-1/2/mode
    ```

    **Discovery:**
    Use `GET /instruments/{klass}/{device_id}/methods` to discover all available
    query methods for a specific device.
    """
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


@app.post(
    "/instruments/{klass}/{device_id}/{channel}/{method}/{param}",
    tags=["instrument-control"],
    summary="Set instrument parameter or control state",
    status_code=204,
    responses={
        204: {"description": "Command executed successfully, no content returned"},
        400: {"description": "Invalid parameters, type conversion failed, or method execution failed"},
        404: {"description": "Invalid class, unknown device, or method not found"}
    }
)
def call_driver_post(
    klass: str = Path(..., description="3-letter instrument class code", example="PSU"),
    device_id: str = Path(..., description="Unique device identifier from configuration", example="psu-1"),
    channel: str = Path(..., regex="^[1-9]$", description="Channel number (1-9)", example="1"),
    method: str = Path(..., description="Method name without 'set_' prefix (e.g., 'voltage', 'current', 'output')", example="voltage"),
    param: str = Path(..., description="Value to set (auto-converted to int/float/bool/string)", example="12.5")
):
    """
    Send a command to set an instrument parameter or control state.

    This is the primary endpoint for controlling instruments. The method name is
    automatically prefixed with `set_` and resolved to the driver method. The param
    value is automatically converted to the appropriate type (int, float, bool, or string).

    **Method Resolution:**
    - Partial name `voltage` → resolves to `set_voltage()` driver method
    - Partial name `current` → resolves to `set_current()` driver method
    - Partial name `output` → resolves to `set_output()` driver method
    - Only methods with `set_` prefix can be called via POST (security feature)

    **Parameter Type Conversion:**
    - `"12.5"` → `12.5` (float)
    - `"5"` → `5` (integer)
    - `"true"` or `"false"` → boolean
    - `"CV"` or other text → string (passed as-is)

    **Common Set Methods:**
    - `voltage`: Set output voltage setpoint (e.g., `12.5` for 12.5V)
    - `current`: Set output current limit (e.g., `2.5` for 2.5A)
    - `output`: Enable/disable output (e.g., `true` or `false`)
    - `mode`: Set operating mode (e.g., `"CV"`, `"CC"`, `"CURR"`, `"VOLT"`)
    - `ovp`: Set over-voltage protection limit
    - `ocp`: Set over-current protection limit

    **Priority Queue Execution:**
    When unified polling is enabled, API requests are queued with HIGH priority
    for immediate execution ahead of background polling operations.

    **Example Requests:**
    ```bash
    # Set PSU channel 1 voltage to 12.5V
    POST /instruments/PSU/psu-1/1/voltage/12.5

    # Set PSU channel 2 current limit to 2.5A
    POST /instruments/PSU/psu-1/2/current/2.5

    # Enable PSU channel 1 output
    POST /instruments/PSU/psu-1/1/output/true

    # Set electronic load mode to constant current
    POST /instruments/OEL/load-1/1/mode/CURR

    # Set function generator frequency to 1000 Hz
    POST /instruments/FGN/gen-1/1/frequency/1000
    ```

    **Discovery:**
    Use `GET /instruments/{klass}/{device_id}/methods` to discover all available
    setter methods for a specific device.

    **Note:** This endpoint returns 204 No Content on success. No response body is sent.
    """
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
