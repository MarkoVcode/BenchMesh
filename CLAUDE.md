# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BenchMesh is a consistent, browser-based cockpit for lab instruments. It connects, controls, logs, correlates, and automates multiple serial devices from a single interface. The core component is `benchmesh-serial-service`, a Python backend with FastAPI that manages concurrent serial connections through a modular driver architecture.

## Architecture

The system follows a layered architecture:

- **SerialManager** (`serial_manager.py`): Central orchestrator that manages device connections, spawns per-device worker threads, maintains device registry with IDN and status data, and handles reconnection logic
- **Driver Layer** (`drivers/`): Modular device-specific drivers (tenma_72, owon_spm, owon_xdm, owon_oel, owon_dge) that implement device-specific protocols and polling
- **Transport Layer** (`transport.py`): SerialTransport abstraction over pyserial for serial communication
- **API Layer** (`api.py`): FastAPI application exposing REST endpoints and WebSocket for device status and control
- **Frontend** (`frontend/`): React+TypeScript UI built with Vite

Each device runs in its own worker thread with per-device RLock for thread safety. Devices reconnect automatically with ~2s backoff on failure. The registry maintains `IDN` (from *IDN? SCPI command on connect) and `status` (polled every ~2s) for each device.

## Common Commands

### Starting the Full System

```bash
# From repository root - starts everything (API, Frontend, Node-RED)
./start.sh

# Services will be available at:
# - Frontend: http://localhost:57666
# - API Docs: http://localhost:57666/docs
# - Node-RED: http://localhost:1880
```

### Backend Development

```bash
# From benchmesh-serial-service/ directory

# Install dependencies
pip install -r requirements.txt

# Run the service (standalone, no API)
python -m benchmesh_service.main --config config.yaml

# Run with FastAPI (includes frontend auto-start)
PYTHONPATH=src uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 57666

# Run tests
pytest tests/

# Run specific test file
pytest tests/test_serial_manager.py

# Run with verbose output
pytest -v tests/
```

### Node-RED

```bash
# From repository root

# Install Node-RED (first time only)
npm install

# Start Node-RED standalone
npm run start:nodered

# Node-RED runs on port 1880
# Data stored in .node-red/ directory
```

### Frontend Development

```bash
# From benchmesh-serial-service/frontend/ directory

# Install dependencies
npm ci

# Development server (hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Run tests once (CI mode)
npm run test:run
```

### Driver CLI Tool

Test driver methods directly from command line:

```bash
# From repository root, set PYTHONPATH if needed
export PYTHONPATH=benchmesh-serial-service/src

# List devices from config
python -m benchmesh_service.tools.driver_cli list --config benchmesh-serial-service/config.yaml

# List available methods for a device
python -m benchmesh_service.tools.driver_cli methods --id tenmapsu-1 --config benchmesh-serial-service/config.yaml

# Call a method (no args)
python -m benchmesh_service.tools.driver_cli call --id tenmapsu-1 --method identify --config benchmesh-serial-service/config.yaml

# Call with positional args
python -m benchmesh_service.tools.driver_cli call --id spm-1 --method set_voltage 5.0 --config benchmesh-serial-service/config.yaml

# Call with kwargs (JSON)
python -m benchmesh_service.tools.driver_cli call --id tenmapsu-1 --method set_output true --kwargs '{"ch":1}' --config benchmesh-serial-service/config.yaml
```

### CI

GitHub Actions runs on all branches and PRs:
- Backend tests: `pytest benchmesh-serial-service/tests`
- Frontend tests: `npx vitest run --reporter=dot`

## Configuration System

Devices are defined in `config.yaml` (YAML v1 schema):

```yaml
version: 1
devices:
  - id: tenmapsu-1              # Unique device ID
    name: "TENMA PSU"            # Display name
    driver: tenma_psu            # Maps to driver folder (aliased to tenma_72)
    port: /dev/tty722540         # Serial port path
    baud: 9600                   # Baud rate
    serial: 8N1                  # Data bits, parity, stop bits
    model: 72-2540               # Optional model override
```

Each driver has a `manifest.json` defining:
- Supported models and their classes (3-letter codes: PSU, SPM, XDM, OEL)
- Per-class polling methods and intervals
- Connection EOL characters (send_eol, recv_eol)
- Driver module path

Manifest aliases in `serial_manager.py` and `manifest_resolver.py` map legacy driver names (e.g., `tenma_psu` → `tenma_72`).

## Adding a New Driver

1. Create driver package: `benchmesh-serial-service/src/benchmesh_service/drivers/<driver_name>/`
2. Create `driver.py` with a class exposing:
   - `identify()` → returns IDN string
   - `poll_status()` → returns status dict
   - Device-specific control methods
3. Create `manifest.json` defining models, classes, polling config, and EOL characters
4. Update `drivers/classes.json` if adding new 3-letter class codes
5. Add driver instantiation logic to `driver_factory.py` if needed
6. Create tests in `tests/` using pytest and mock serial communication

Driver should accept `transport: SerialTransport` in constructor and use it for all communication.

## Key Modules

- `serial_manager.py`: SerialManager orchestrates all device connections and worker threads
- `manifest_resolver.py`: Resolves driver manifests to extract class, polling, and EOL configuration
- `driver_factory.py`: Instantiates driver classes from string names and device configs
- `poll_worker.py`: DeviceWorker runs per-device polling loop in dedicated thread
- `registry.py`: DeviceRegistry thread-safe storage for device IDN and status
- `transport.py`: SerialTransport wraps pyserial with EOL handling
- `api.py`: FastAPI app with endpoints `/status`, `/instruments`, `/api/call`, and WebSocket `/ws`
- `connection.py`: DeviceConnection tracks connection state per device
- `reconnect.py`: ReconnectPolicy implements backoff strategy

## Testing Notes

- Tests use `pytest` with fixtures in `conftest.py`
- Mock serial communication using `unittest.mock.Mock` for transport
- Tests in `tests/` cover: manifest resolution, driver factory, serial manager behavior, concurrency, polling, and edge cases
- Frontend uses `vitest` with `@testing-library/react`

## Environment Variables

- `BENCHMESH_CONFIG`: Path to config.yaml (default: `config.yaml`)
- `API_PORT`: FastAPI port (default: `57666`)
- `UI_PORT`: Frontend dev server port (default: `52893`)

## Notes

- Repository root contains example RS232 test scripts in `system/` directory
- Documentation and udev rules in `system/udev_rules.txt` for persistent device paths
- Driver manifests support per-class polling intervals (e.g., PSU class polls every 2s, SPM every 3s)
- Frontend proxies API requests to backend during development via Vite config

## Guidelines

- apply TDD principles when adding new features
- always run tests after the code changes