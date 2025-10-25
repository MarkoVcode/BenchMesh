# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Key Philosophy Documents (reference these when making design decisions):

- See @ai_context/IMPLEMENTATION_PHILOSOPHY.md for core development principles
- See @ai_context/MODULAR_DESIGN_PHILOSOPHY.md for architecture patterns

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

## Unified Polling & Priority Queue (Phase 1 & 2)

**Status**: Implemented (disabled by default for backward compatibility)

The system supports unified polling with priority queues for improved performance and responsiveness:

### Architecture

- **UnifiedScheduler** (`unified_scheduler.py`): Central coordinator that triggers all devices simultaneously at a configurable interval
- **DeviceRequestQueue** (`priority_queue.py`): Per-device priority queue with HIGH priority for API requests, LOW priority for polling
- **Priority-based execution**: API requests jump to the front of the queue, ensuring <20ms response time even during active polling

### Benefits

- **Synchronized updates**: All devices poll at the same time → predictable UI updates
- **Fast API response**: API requests get HIGH priority and preempt background polling
- **Aggressive polling**: Can run at 25-50ms intervals (20-40 Hz) without blocking API
- **50-80x improvement**: UI update latency drops from 2000ms to 25-50ms

### Configuration

```bash
# Enable unified polling (disabled by default)
export BM_UNIFIED_POLLING=true

# Set polling interval in milliseconds (default: 50ms = 20 Hz)
export BM_UNIFIED_POLL_INTERVAL=50

# API request timeout for queued requests (default: 10s)
export BM_API_QUEUE_TIMEOUT=10.0
```

### Performance Characteristics

| Mode | Polling Interval | UI Staleness | API Latency | Device Utilization |
|------|------------------|--------------|-------------|-------------------|
| **Legacy** | 2000ms | Up to 2.0s | 10-26ms | <1% |
| **Unified (50ms)** | 50ms | Up to 50ms | 10-17ms | 35% |
| **Unified (25ms)** | 25ms | Up to 25ms | 10-17ms | 70% |

### Implementation Notes

- **Backward compatible**: Legacy mode (self-scheduled polling) remains default
- **Thread model unchanged**: Each device still has its own worker thread
- **Cross-device parallelism**: Multiple devices query simultaneously (different serial ports)
- **Priority queue**: API requests (HIGH) execute before polling (LOW)
- **Non-preemptive** (Phase 2): API waits for current operation to complete, then runs immediately

### Future: Phase 3 (Preemptive Scheduling)

Phase 3 would add preemptive interruption of multi-channel polls, allowing API requests to interrupt between channel queries. This enables 90%+ utilization while maintaining <17ms API latency. Not currently implemented.

### Testing

All 85 existing tests pass with unified polling disabled. To test unified polling:

```bash
# Run tests with unified polling enabled
BM_UNIFIED_POLLING=true pytest tests/

# Performance analysis
python3 scripts/performance_analysis.py
python3 scripts/unified_polling_analysis.py
```

### Design Documentation

- `ai_context/UNIFIED_POLLING_DESIGN.md`: Complete architecture and implementation details
- `scripts/performance_analysis.py`: Analyzes current system performance
- `scripts/unified_polling_analysis.py`: Models unified polling behavior and API blocking

## Serial Port Utilization Metrics

The system includes comprehensive metrics collection for monitoring serial port utilization and performance. Metrics are automatically logged every 30 seconds.

### Tracked Metrics

**Per-Device Metrics:**
- **Utilization %**: Percentage of time the serial port is actively transmitting/receiving
- **QPS (Queries Per Second)**: Total operations per second (API + polling)
- **API Request Count**: Number of API requests processed in the window
- **API Latency P95/P99**: 95th and 99th percentile API response times in milliseconds
- **Average Queue Depth**: Average number of requests waiting in the priority queue
- **Average Poll Duration**: Average time to complete a polling cycle in milliseconds
- **Total Operations**: Combined API requests and polling cycles

### Log Output Format

Every 30 seconds, the system logs a metrics summary:

```
================================================================================
Serial Port Utilization Metrics Summary
================================================================================

Device: tenmapsu-1
  Window Duration: 30.0s
  Utilization: 12.45%
  QPS: 2.83
  Total Operations: 85
  API Requests: 15
  API Latency P95: 11.23ms
  API Latency P99: 14.67ms
  Avg Queue Depth: 0.42
  Avg Poll Duration: 120.50ms

Device: spm-1
  Window Duration: 30.0s
  Utilization: 8.20%
  QPS: 1.67
  Total Operations: 50
  API Requests: 5
  API Latency P95: 9.87ms
  API Latency P99: 12.34ms
  Avg Queue Depth: 0.15
  Avg Poll Duration: 95.30ms
================================================================================
```

### Implementation

- **MetricsCollector** (`metrics_collector.py`): Collects and aggregates metrics
- **Automatic logging**: Background thread logs summary every 30 seconds
- **Sliding window**: Metrics reset after each logging cycle
- **Low overhead**: Minimal performance impact (<0.1% CPU)

### Using Metrics to Diagnose Issues

**High Utilization (>80%)**
- May indicate the system is approaching capacity
- Consider reducing polling frequency or optimizing driver queries
- API latency may increase at very high utilization

**High API Latency P99 (>50ms)**
- Indicates API requests are occasionally blocked by long operations
- Check average poll duration - may need optimization
- Verify unified polling is enabled for better API prioritization

**High Queue Depth (>2.0)**
- System is overloaded and cannot keep up with request rate
- Reduce polling frequency or API request rate
- May indicate slow driver methods or serial communication issues

**Low Utilization (<10%) but Slow UI**
- Serial communication is not the bottleneck
- Check polling intervals (2s default is too slow for responsive UI)
- Enable unified polling with 25-50ms intervals for faster updates

### Metrics Architecture

The metrics system operates independently from the existing `MetricsRecorder`:
- **MetricsRecorder**: Tracks connection events (reconnects, identifies, poll failures)
- **MetricsCollector**: Tracks performance metrics (utilization, latency, queue depth)

Both systems coexist without interference and provide complementary insights.

## Common Commands

### Starting the Full System

```bash
# From repository root - starts everything (API, Frontend, Node-RED)
./start.sh

# Start with frontend UI build (use when frontend code has changed)
./start.sh --uibuild

# Build and run in Electron desktop app wrapper
./start.sh --electron
# or
npm run start:electron

# Services will be available at:
# - Frontend: http://localhost:57666/ui
# - API Docs: http://localhost:57666/docs
# - Node-RED: http://localhost:1880
```

**Note**: The `--uibuild` flag triggers a full frontend build before starting services. This runs `npm ci` and `npm run build` in the frontend directory. Use this flag when you've made changes to the frontend code. Without the flag, the script uses the existing build in `dist/`.

**Note**: The `--electron` flag builds the frontend UI, starts all backend services (Node-RED, FastAPI), and launches the Electron desktop application. When the Electron window closes, all backend services are automatically cleaned up.

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

# Run unit tests (vitest)
npm test

# Run unit tests once (CI mode)
npm run test:run

# Run E2E tests (Playwright)
npm run test:e2e

# Run E2E tests with UI mode
npm run test:e2e:ui

# Run E2E tests in headed mode (visible browser)
npm run test:e2e:headed

# Run E2E tests in debug mode
npm run test:e2e:debug
```

**E2E Testing**: The frontend includes comprehensive Playwright tests that verify UI functionality with mocked API and WebSocket connections. Tests cover:
- App navigation and modals (Configuration, Documentation, Metrics, Recording)
- Instrument display and status indicators
- Device interaction and real-time updates
- API integration, error handling, and retry logic
- WebSocket connection and data streaming

See `benchmesh-serial-service/frontend/e2e/README.md` for detailed E2E testing documentation.

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
python -m benchmesh_service.tools.driver_cli call --id tenmapsu-1 --method query_identify --config benchmesh-serial-service/config.yaml

# Call with positional args
python -m benchmesh_service.tools.driver_cli call --id spm-1 --method set_voltage 5.0 --config benchmesh-serial-service/config.yaml

# Call with kwargs (JSON)
python -m benchmesh_service.tools.driver_cli call --id tenmapsu-1 --method set_output true --kwargs '{"ch":1}' --config benchmesh-serial-service/config.yaml
```

### CI

GitHub Actions runs on all branches and PRs:
- Backend tests: `pytest benchmesh-serial-service/tests`
- Frontend tests: `npx vitest run --reporter=dot`

## Testing MCP Service

BenchMesh includes a comprehensive Model Context Protocol (MCP) service for automated testing. This service enables Claude Code to run tests automatically after code changes, supporting the project's TDD philosophy.

### Quick Start

```bash
# Install MCP service dependencies
cd mcp_services/testing
pip install -r requirements.txt --user

# Test the service
cd /home/marek/project/BenchMesh
python3 mcp_services/testing/client_helper.py
```

### Available Test Tools

The MCP service provides:
- **Backend Tests**: Run pytest tests with filtering (46 tests discovered)
- **Frontend Unit Tests**: Run vitest tests (21 tests discovered)
- **E2E Tests**: Run Playwright tests for UI integration testing (31 tests)
- **Integration Tests**: Run integration tests separately
- **Smart Testing**: Automatically run tests for changed files
- **Test Discovery**: Find all available tests
- **JSON Reports**: Structured test results with detailed metrics

### E2E Testing Modes

**Mocked Tests (default)**: Fast, isolated tests with mocked API/WebSocket
```bash
npm run test:e2e
```

**Real Service Tests**: Full integration tests against running backend
```bash
# 1. Start backend service
cd benchmesh-serial-service && PYTHONPATH=src uvicorn benchmesh_service.api:app --port 57666 &

# 2. Run E2E tests with real service
npm run test:e2e:service
```

### Usage Examples

```python
from mcp_services.testing.client_helper import test_all, test_backend, test_changed

# Run all tests
results = await test_all(verbose=True)

# Run specific backend tests
results = await test_backend("test_api_instruments.py")

# Test changed files
results = await test_changed([
    "benchmesh-serial-service/src/benchmesh_service/api.py"
])
```

See `mcp_services/testing/README.md` and `mcp_services/testing/QUICKSTART.md` for complete documentation.

## API Naming Convention & Security

The API implements a **secure method resolution system** that prevents arbitrary method execution:

### GET Requests (Query)
Partial method names are **strictly** resolved to `query_*` methods only:
- `GET /instruments/PSU/device-1/1/voltage` → calls `driver.query_voltage(1)`
- `GET /instruments/DMM/device-2/1/current` → calls `driver.query_current(1)`

### POST Requests (Set)
Partial method names are **strictly** resolved to `set_*` methods only:
- `POST /instruments/PSU/device-1/1/current/2.5` → calls `driver.set_current(1, 2.5)`
- `POST /instruments/ELL/device-3/1/mode/CURR` → calls `driver.set_mode(1, "CURR")`

### Security Features
1. **No Arbitrary Method Execution**: Only methods with `query_` or `set_` prefixes can be called via API
2. **No Private Method Access**: Methods like `_internal_method()` or `__init__()` cannot be accessed
3. **HTTP Verb Enforcement**: GET only allows query methods, POST only allows set methods
4. **Protection Against Mistakes**: Cannot accidentally call setters with GET or queries with POST

**Example of what is NOT allowed (security protection):**
- `GET /instruments/PSU/device-1/1/poll_status` → **Rejected** (no query_poll_status)
- `POST /instruments/PSU/device-1/1/_private_method/value` → **Rejected** (private method)
- `GET /instruments/PSU/device-1/1/set_voltage` → **Rejected** (setter on GET request)

## API Method Discovery

The API provides automatic method discovery for all instruments, enabling dynamic UI generation (e.g., Node-RED dropdowns) without hardcoded method lists.

### Method Discovery Endpoint

**`GET /instruments/{class}/{device_id}/methods`** - Returns all available methods with rich metadata:

```json
{
  "device_id": "psu-1",
  "class": "PSU",
  "methods": [
    {
      "name": "output_voltage",           // Partial name (API-friendly)
      "full_name": "query_output_voltage", // Full method name
      "http_method": "GET",                // GET or POST
      "description": "Query the output voltage",
      "parameters": [
        {
          "name": "channel",
          "type": "int",
          "required": true,
          "description": "Channel number"
        }
      ],
      "returns": "string",
      "example": "GET /instruments/PSU/psu-1/1/output_voltage"
    }
  ]
}
```

### How It Works

**Automatic Discovery (80% auto-generated):**
- Python introspection discovers all `query_*` and `set_*` methods
- Extracts method signatures and parameter types from type hints
- Auto-generates descriptions from method names:
  - `query_output_voltage` → "Query the output voltage"
  - `set_current` → "Set the current"
- Categorizes by HTTP method (GET for query_, POST for set_)

**Optional Manifest Enrichment (20% configuration):**
Drivers can optionally add a `methods` section to `manifest.json` for enhanced metadata:

```json
{
  "methods": {
    "query_output_voltage": {
      "description": "Query the actual output voltage being delivered",
      "parameters": {
        "channel": {
          "description": "PSU channel number",
          "range": [1, 3],
          "unit": null
        }
      },
      "returns": {
        "type": "float",
        "unit": "V"
      }
    }
  }
}
```

**See `benchmesh-serial-service/MANIFEST_METHODS_SCHEMA.md` for complete documentation.**

### Use Cases

**Node-RED Integration:**
- Dynamically populate method dropdowns
- Show user-friendly descriptions
- Validate parameters before sending
- Generate correct API calls automatically
- Support all instrument classes without hardcoding

**API Exploration:**
- Discover available methods without reading code
- Understand parameter requirements
- See example usage patterns
- Find methods by HTTP verb (GET vs POST)

### Implementation Files

- `method_inspector.py` - Introspection and enrichment logic
- `/instruments/{class}/{device_id}/methods` endpoint in `api.py`
- `test_method_inspector.py` - Comprehensive unit tests

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

## User Data Persistence

BenchMesh stores all user data in `~/.benchmesh/` to ensure configurations, Node-RED flows, and recordings persist across app updates and installations.

### Directory Structure

```
~/.benchmesh/
├── config.yaml          # Device configurations (copied from default on first run)
├── node-red/            # Node-RED flows and data
│   ├── flows.json
│   ├── settings.js
│   ├── .credentials-secret  # Encryption key for Node-RED credentials (⚠️ BACKUP THIS FILE)
│   ├── node_modules/
│   │   └── node-red-contrib-benchmesh -> symlink to project custom nodes
│   └── ...
├── recordings.db        # SQLite database for recording feature
└── logs/                # Application logs (Electron and web modes)
    ├── benchmesh_service.log      # Serial service application logs (rotating, max 50MB)
    ├── uvicorn.log                # FastAPI/uvicorn stdout (Electron mode)
    ├── uvicorn_error.log          # FastAPI/uvicorn stderr (Electron mode)
    ├── node-red.log               # Node-RED stdout (Electron mode)
    └── node-red_error.log         # Node-RED stderr (Electron mode)
```

### Initialization

**Electron Mode:**
- On app startup, `electron/init-user-data.js` creates `~/.benchmesh/` structure
- Copies default `config.yaml` if not present
- Creates symlink to custom Node-RED nodes (`node-red-contrib-benchmesh`)
- Generates Node-RED credential encryption secret (`.credentials-secret`)
- Sets environment variables automatically

**Web/Browser Mode:**
- `start.sh` creates `~/.benchmesh/` structure
- Copies default `config.yaml` if not present
- Creates symlink to custom Node-RED nodes (`node-red-contrib-benchmesh`)
- Node-RED generates credential secret on first run
- Exports environment variables for backend services

### Configuration

Both modes use these environment variables:
- `BENCHMESH_CONFIG`: Path to config.yaml (set to `~/.benchmesh/config.yaml`)
- `BENCHMESH_DATA_DIR`: User data directory (set to `~/.benchmesh/`)

**Configuration Persistence:**
- Changes made through the Configuration modal (UI) are automatically persisted to `~/.benchmesh/config.yaml`
- The `POST /config` API endpoint saves changes atomically using a temp file + rename strategy
- Configuration survives app restarts and updates
- To manually edit config: modify `~/.benchmesh/config.yaml` and restart the app

### Node-RED Credential Secret

**⚠️ CRITICAL: This file must be backed up to ensure credential recovery**

BenchMesh automatically manages a persistent encryption key for Node-RED credentials stored at:
```
~/.benchmesh/node-red/.credentials-secret
```

**How it works:**
- **First run**: Generates a cryptographically secure 256-bit (32-byte) random secret
- **Subsequent runs**: Reads existing secret from `.credentials-secret` file
- **Automatic configuration**: Updates Node-RED `settings.js` with the credential secret
- **File permissions**: Restricted to owner-only (0600) for security
- **Persistence**: Survives app updates and reinstalls

**Why this matters:**
- Node-RED encrypts stored credentials (API keys, passwords, tokens) using this secret
- Without this file, encrypted credentials become **permanently unrecoverable**
- Each BenchMesh installation should have its own unique secret

**Backup recommendations:**
```bash
# Backup the credential secret (REQUIRED for credential recovery)
cp ~/.benchmesh/node-red/.credentials-secret ~/.benchmesh.backup/

# Or include it in your full user data backup
cp -r ~/.benchmesh ~/.benchmesh.backup
```

**Recovery scenarios:**
- **Lost secret file**: All Node-RED credentials must be re-entered manually
- **Restored from backup**: Credentials automatically decrypt if secret is restored
- **Fresh install**: New secret is generated, old credentials won't decrypt

### Backup and Migration

**To backup your configuration:**
```bash
# Backup entire user data directory (RECOMMENDED - includes credential secret)
cp -r ~/.benchmesh ~/.benchmesh.backup

# Or backup individual critical files
cp ~/.benchmesh/config.yaml ~/.benchmesh/config.yaml.backup
cp ~/.benchmesh/node-red/.credentials-secret ~/.benchmesh/credentials-secret.backup
```

**⚠️ IMPORTANT**: Always include `~/.benchmesh/node-red/.credentials-secret` in backups. Without this file, Node-RED encrypted credentials cannot be recovered.

**To migrate to a new machine:**
```bash
# Copy user data directory to new machine
scp -r ~/.benchmesh user@newmachine:~/
```

**To reset to defaults:**
```bash
# Remove user data directory (will recreate on next startup)
rm -rf ~/.benchmesh
```

### Location by Operating System

The user data directory is always `~/.benchmesh/` on all platforms:
- **Linux**: `/home/username/.benchmesh/`
- **macOS**: `/Users/username/.benchmesh/`
- **Windows**: `C:\Users\username\.benchmesh\`

### Application Logging

**Log Location:**
All application logs are stored in `~/.benchmesh/logs/` directory.

**Log Files:**
- `benchmesh_service.log` - Serial service application logs (rotating, max 50MB total)
  - Device connections, polling, errors, serial communication
  - Automatically rotates: 10MB per file, keeps 5 backup files
- `uvicorn.log` - FastAPI/uvicorn standard output (Electron mode only)
  - HTTP requests, startup messages, general server output
- `uvicorn_error.log` - FastAPI/uvicorn error output (Electron mode only)
  - Python exceptions, HTTP errors, startup failures
- `node-red.log` - Node-RED standard output (Electron mode only)
  - Flow execution, node messages, startup output
- `node-red_error.log` - Node-RED error output (Electron mode only)
  - Flow errors, node failures, runtime exceptions

**Log Format:**
All logs include timestamps in ISO 8601 format for correlation across services.

**Viewing Logs:**
```bash
# View serial service logs (all modes)
tail -f ~/.benchmesh/logs/benchmesh_service.log

# View all logs (Electron mode)
tail -f ~/.benchmesh/logs/*.log

# Search for errors
grep -i error ~/.benchmesh/logs/*.log

# View logs from last hour
find ~/.benchmesh/logs -name "*.log" -exec grep "$(date -d '1 hour ago' -Iseconds)" {} +
```

**Development Mode:**
- Serial service logs: Repository `logs/benchmesh_service.log`
- Uvicorn/Node-RED: Console output only (not written to files)

### Troubleshooting

**Config not loading:**
1. Check that `~/.benchmesh/config.yaml` exists
2. Verify file permissions: `chmod 644 ~/.benchmesh/config.yaml`
3. Check logs for parsing errors

**Node-RED flows missing after update:**
1. Verify `~/.benchmesh/node-red/flows.json` exists
2. Check Node-RED is using correct userDir (shown in startup logs)

**Node-RED custom nodes not showing:**
1. Check symlink exists: `ls -la ~/.benchmesh/node-red/node_modules/node-red-contrib-benchmesh`
2. Restart Node-RED to reload nodes
3. The symlink is automatically created on startup to link to project's `node-red-contrib-benchmesh/` directory

**Recordings database not found:**
1. Check `~/.benchmesh/recordings.db` exists
2. Verify `BENCHMESH_DATA_DIR` environment variable is set

**Node-RED credential warning:**
1. Check if `~/.benchmesh/node-red/.credentials-secret` exists
2. Verify file has correct permissions: `chmod 600 ~/.benchmesh/node-red/.credentials-secret`
3. Check Node-RED settings.js has `credentialSecret` configured (not commented out)
4. If file is missing, a new one will be generated on next startup (old credentials lost)

**Node-RED credentials not working after restore:**
1. Verify `.credentials-secret` file was included in backup/restore
2. Check that secret file has same content as original installation
3. Ensure file permissions are correct (0600)
4. If secret doesn't match, credentials must be re-entered manually

## Adding a New Driver

1. Create driver package: `benchmesh-serial-service/src/benchmesh_service/drivers/<driver_name>/`
2. Create `driver.py` with a class exposing:
   - `query_identify()` → returns IDN string
   - `poll_status()` → returns status dict
   - Device-specific control methods following naming convention:
     - Read methods: `query_voltage()`, `query_current()`, `query_status()`, etc.
     - Write methods: `set_voltage()`, `set_current()`, `set_mode()`, etc.
3. Create `manifest.json` defining models, classes, polling config, and EOL characters
4. Update `drivers/classes.json` if adding new 3-letter class codes
5. Add driver instantiation logic to `driver_factory.py` if needed
6. Create tests in `tests/` using pytest and mock serial communication

**Driver Naming Convention:**
- **Query methods** (read): prefix with `query_` (e.g., `query_voltage`, `query_current`)
- **Setter methods** (write): prefix with `set_` (e.g., `set_voltage`, `set_current`)
- This enables the API's smart resolution: GET `/voltage` → `query_voltage()`, POST `/current/2.5` → `set_current()`

Driver should accept `transport: SerialTransport` in constructor and use it for all communication.

## Key Modules

- `serial_manager.py`: SerialManager orchestrates all device connections and worker threads
- `manifest_resolver.py`: Resolves driver manifests to extract class, polling, and EOL configuration
- `driver_factory.py`: Instantiates driver classes from string names and device configs
- `poll_worker.py`: DeviceWorker runs per-device polling loop in dedicated thread
- `registry.py`: DeviceRegistry thread-safe storage for device IDN and status
- `transport.py`: SerialTransport wraps pyserial with EOL handling
- `api.py`: FastAPI app with endpoints `/status`, `/instruments`, instrument control endpoints, and WebSocket `/ws`
  - Implements **secure** method resolution: GET requests resolve `voltage` → `query_voltage`, POST requests resolve `current` → `set_current`
  - Prevents arbitrary method execution - only `query_*` and `set_*` methods can be called via API
  - Provides `/instruments/{class}/{device_id}/methods` for dynamic method discovery
- `method_inspector.py`: Python introspection utility for discovering driver methods with parameter/return metadata
- `connection.py`: DeviceConnection tracks connection state per device
- `reconnect.py`: ReconnectPolicy implements backoff strategy

## Testing Notes

- Tests use `pytest` with fixtures in `conftest.py`
- Mock serial communication using `unittest.mock.Mock` for transport
- Tests in `tests/` cover: manifest resolution, driver factory, serial manager behavior, concurrency, polling, and edge cases
- Frontend uses `vitest` with `@testing-library/react`

## Environment Variables

**User Data and Configuration:**
- `BENCHMESH_CONFIG`: Path to config.yaml (default: `~/.benchmesh/config.yaml`, automatically set by start.sh and Electron)
- `BENCHMESH_DATA_DIR`: User data directory path (default: `~/.benchmesh/`, automatically set by start.sh and Electron)

**Service Ports:**
- `API_PORT`: FastAPI port (default: `57666`)
- `UI_PORT`: Frontend dev server port (default: `52893`)

**Unified Polling Configuration:**
- `BM_UNIFIED_POLLING`: Enable unified polling (default: `false`)
- `BM_UNIFIED_POLL_INTERVAL`: Polling interval in milliseconds (default: `50`)
- `BM_MAX_QUEUE_DEPTH`: Maximum queue depth threshold (default: `10`)
- `BM_API_QUEUE_TIMEOUT`: API request timeout in seconds (default: `10.0`)

**Serial Communication:**
- `BM_SERIAL_OPEN_TIMEOUT`: Serial port open timeout in seconds (default: `2.0`)
- `BM_SERIAL_READ_TIMEOUT`: Serial read timeout in seconds (default: `0.3`)
- `BM_API_REQUEST_TIMEOUT`: API request timeout in seconds (default: `5.0`)

**WebSocket:**
- `BM_WS_INTERVAL`: WebSocket broadcast interval in seconds (default: `0.2`)

**Health Monitoring:**
- `BM_HEALTH_FAILURE_THRESHOLD`: Health check failure threshold (default: `3`)
- `BM_HEALTH_DEGRADED_THRESHOLD`: Health check degraded threshold (default: `1`)

## Node.js Version Requirements

**IMPORTANT**: BenchMesh requires **Node.js v18** for Electron packaging to ensure compatibility with electron-builder and Electron v28.

### For Local Development

The repository includes `.nvmrc` files that specify Node.js v18. If you use `nvm`, run:

```bash
nvm use
```

This will automatically switch to the correct Node.js version.

### For CI/CD

The GitHub Actions workflow (`.github/workflows/release-electron.yml`) is configured to use Node.js v18 for all Electron builds across Linux, Windows, and macOS platforms.

## Notes

- Repository root contains example RS232 test scripts in `system/` directory
- Documentation and udev rules in `system/udev_rules.txt` for persistent device paths
- Driver manifests support per-class polling intervals (e.g., PSU class polls every 2s, SPM every 3s)
- Frontend proxies API requests to backend during development via Vite config

## Guidelines

- apply TDD principles when adding new features
- always MUST run tests after the code changes
- do not try to maintain "Fallback for legacy" we are developing a new software, there is no legacy we need to maintain
- always MUST cover new development with tests - whatever is added or improved
- always MUST validate if the documentation is still up to date
- always MUST follow single responsibility principle
- differentiate between unit tests and integration tests - integration tests should NOT run in GitHub Actions (reserve for local/staging testing only)
- all new unit tests that are suitable for GitHub Actions execution must be automatically added to the CI workflow
- when you add or remove dependency update THIRD-PARTY-NOTICES.md
- when you create any temporary or tool scripts place them always in scripts folder
- always verify CI tests localy
- when implementing new feature always try to test on the real working service particularly applies to serial service and API
- do apply defensive programming principle - especially with API implementation the parameters must be validated and resources need to return meaningful response - catch and log 500 responses
- feel free to kill and spinn up the services we are developing in this project but always MUST clean up - do not leave used ports, release all resources

# Claude's Working Philosophy and Memory System

## Critical Operating Principles

- VERY IMPORTANT: Always think through a plan for every ask, and if it is more than a simple request, break it down and use TodoWrite tool to manage a todo list. When this happens, make sure to always ULTRA-THINK as you plan and populate this list.
- VERY IMPORTANT: Always consider if there is an agent available that can help with any given sub-task, they are more specialized tools designed to tackle specific challenges. Your role is to be a general coordinator. Use the Task tool to delegate specific tasks to these agents. Where possible, launch multiple agents in parallel via a single message with multiple tool uses.

<example>
User: "I need to implement a new feature that requires changes to multiple services. [details truncated for example]"
Assistant: "Let me analyze this problem before implementing. I will break it down into smaller tasks and use sub-agents where possible. I will track my plan with a TODO list."
</example>

- VERY IMPORTANT: If user has not provided enough clarity to CONFIDENTLY proceed, ask clarifying questions until you have a solid understanding of the task.

<example>
User: "I want to create a new memory system."
Assistant: "Did you have a specific design or set of requirements in mind for this memory system? Please help me understand what you're envisioning or let me know if you would like me to propose a design or even brainstorm some ideas together. Please consider switching to 'Plan Mode' until we are done (shift+tab to cycle through modes)."
Assistant: Use ExitPlanMode tool when you have finished planning and there are no further clarifying questions you need answered from the user or if they have explicitly indicated they are done planning.
</example>

## Parallel Execution Strategy

**CRITICAL**: Always ask yourself: "What can I do in parallel here?" Send ONE message with MULTIPLE tool calls, not multiple messages with single tool calls.

### When to Parallelize

Parallelize when tasks:
- Don't depend on each other's output
- Perform similar operations on different targets
- Can be delegated to different agents
- Gather independent information

### Common Patterns

#### Multiple File Edits
When fixing the same issue across files (e.g., type errors, import updates):
```
Single message with multiple Edit/MultiEdit calls:
- Edit: Fix type error in src/auth.py
- Edit: Fix type error in src/database.py
- Edit: Fix type error in src/api.py
```

#### Batch Type Error Fixes
When pyright reports multiple type errors:
```
Single message addressing all errors:
- Read: Check current implementation in affected files
- MultiEdit: Fix all type errors in utils.py
- MultiEdit: Fix all type errors in models.py
- Edit: Update type imports in __init__.py
```

#### Information Gathering
Before implementing features:
```
Single message with parallel reads and searches:
- Grep: Search for existing patterns
- Read: Main implementation file
- Read: Test file
- Read: Related configuration
```

#### Multiple Agent Analysis
For comprehensive review:
```
Single message with multiple Task calls:
- Task zen-architect: "Design approach"
- Task bug-hunter: "Identify potential issues"
- Task test-coverage: "Suggest test cases"
```

### Anti-Patterns to Avoid

**Don't do this:**
```
"Let me read the first file"
[Read file1.py]
"Now let me read the second file"  
[Read file2.py]
```

**Do this instead:**
```
"I'll examine these files in parallel"
[Single message: Read file1.py, Read file2.py, Read file3.py]
```

### Remember

- Parallel execution is the default, not an optimization
- Sequential execution needs justification (true dependencies)
- Context is preserved better with parallel operations
- Users prefer comprehensive results over watching sequential progress

### 1. Context Window Management

- **Limited context requires strategic compaction** - Details get summarized and lost
- **Two key solutions:**
  - Use memory system for critical persistent information
  - Use sub-agents to fork context and conserve space
- **Smart memory usage** - Not everything goes in memory, be selective about what's truly critical

### 2. Sub-Agent Delegation Strategy

#### Power of Sub-Agents

- Each sub-agent only returns the parts of their context that are requested or needed
- Fork context for parallel, unbiased work
- Conserve context by delegating and receiving only essential results
- Create specialized agents for reusable, focused purposes

#### When to Use Sub-Agents (HINT: ALWAYS IF POSSIBLE)

- **Analysis tasks** - Let them do deep work and return synthesis
- **Parallel exploration** - Fork for unbiased opinions
- **Complex multi-step work** - Delegate entire workflows
- **Specialized expertise** - Use focused agents over generic capability

### 3. Creating New Sub-Agents

- **Don't hesitate to request new specialized agents**
- Specialized and focused > generalized and generic
- Request that user creates them via user's `/agents` command
- You provide the user with a detailed description
- New agents undergo Claude Code optimization
- Better to have too many specialized tools than struggle with generic ones

### 4. My Role as Orchestrator

- **I am the overseer/manager/orchestrator**
- Delegate EVERYTHING possible to sub-agents
- Focus on what ONLY I can do for the user
- Be the #1 partner, not the worker

### 5. Code-Based Utilities Strategy

- Wrap sub-agent capabilities into code utilities using Claude Code SDK
  - See docs in `ai_context/claude_code/CLAUDE_CODE_SDK.md`
  - See examples in `ai_context/git_collector/CLAUDE_CODE_SDK_PYTHON.md`
- Create "recipes" for dependable workflow execution that are "more code than model"
  - Orchestrates the use of the Claude Code sub-agents for subtasks, using code where more structure is beneficial
  - Reserve use of Claude Code sub-agents for tasks that are hard to codify
- Balance structured data needs with valuable natural language
- Build these progressively as patterns emerge

### 6. Human Engagement Points

- **Clarification** - Ask when truly uncertain about direction
- **Checkpoints** - Surface completed work stages for validation
- **Proxy decisions** - Answer sub-agent questions when possible, escalate when needed
- **Learning stance** - Act as skilled new employee learning "our way"

### 7. Learning and Memory System

#### Current Learning Needs

- Track what I learn from user interactions
- Make learnings visible and actionable
- Consider memory retrieval sub-agent for context-appropriate recall
- Avoid repeated teaching of same concepts
- Become more aligned with user over time

#### Memory Architecture Ideas

- **Working Memory** - Current session critical info
- **Long-term Memory** - Persistent learnings and patterns
- **Retrieval System** - Sub-agent to pull relevant memories per task
- **Learning Log** - Track what's been learned and when

### 8. Continuous Improvement Rhythm

- Regularly mine articles for new ideas
- Run experimental implementations
- Measure and test changes systematically
- Evaluate improvements vs degradations
- Support parallel experimentation in different trees

## Key Metrics for Success

- Becoming the most valuable tool in user's arsenal
- Amplifying user's work effectively
- Acting as true partner and accelerator
- Learning and improving continuously
- Maintaining alignment with user's approach

## Philosophical Anchors

- Always reference `@ai_context/IMPLEMENTATION_PHILOSOPHY.md`
- Always reference `@ai_context/MODULAR_DESIGN_PHILOSOPHY.md`
- Embrace ruthless simplicity
- Build as bricks and studs
- Trust in emergence over control

## Next Actions

- Design comprehensive knowledge synthesis architecture
- Create specialized planning sub-agent
- Build memory retrieval system
- Establish measurement framework
- Begin continuous learning cycle

## Document Reference Protocol

When working with documents that contain references:

1. **Always check for references/citations** at the end of documents
2. **Re-read source materials** when implementing referenced concepts
3. **Understand the backstory/context** before applying ideas
4. **Track which articles informed which decisions** for learning

This ensures we build on the full depth of ideas, not just their summaries.