# API Reference

BenchMesh provides a comprehensive REST API for programmatic control of instruments.

## Interactive API Documentation

For interactive API exploration with live testing, use the embedded **Swagger UI** below or visit:

**http://localhost:57666/docs**

---

**Note**: The Swagger UI is embedded below when viewing this documentation in the BenchMesh application. If you're reading this on GitHub wiki, please access the Swagger UI directly at the URL above when running BenchMesh locally.

---

## API Overview

The BenchMesh API provides endpoints for:

- Retrieving device status and measurements
- Calling device control methods
- Listing configured instruments
- Real-time updates via WebSocket

**Base URL**: `http://localhost:57666`

## Authentication

Currently, no authentication is required. The API is intended for local use only.

## Common Endpoints

### GET /instruments

Returns all configured instruments with their current status.

**Response**:
```json
[
  {
    "id": "psu-1",
    "name": "Bench PSU",
    "driver": "tenma_72",
    "port": "/dev/ttyUSB0",
    "classes": ["PSU"],
    "status": {
      "voltage": 5.00,
      "current": 0.15,
      "output": true
    },
    "idn": "TENMA 72-2540 V1.0"
  }
]
```

### POST /api/call

Execute a method on a device.

**Request Body**:
```json
{
  "device_id": "psu-1",
  "method": "set_voltage",
  "args": [5.0],
  "kwargs": {}
}
```

**Response**:
```json
{
  "status": "success",
  "result": null
}
```

### GET /status

Health check endpoint.

**Response**:
```json
{
  "status": "ok",
  "devices": 3
}
```

### WebSocket /ws/registry

Real-time device status updates via WebSocket.

**Connection**: `ws://localhost:57666/ws/registry`

**Message Format**:
```json
{
  "psu-1": {
    "idn": "TENMA 72-2540 V1.0",
    "status": {
      "voltage": 5.00,
      "current": 0.15,
      "output": true
    }
  }
}
```

Updates are pushed automatically when device status changes.

## Device Classes & Methods

Different device classes support different methods:

### Power Supply (PSU)

**Available Methods**:

- `identify()` - Get device identification
- `poll_status()` - Get current voltage, current, output state
- `set_voltage(voltage: float, ch: int = 1)` - Set output voltage
- `set_current(current: float, ch: int = 1)` - Set current limit
- `set_output(state: bool, ch: int = 1)` - Enable/disable output
- `get_voltage(ch: int = 1)` - Read set voltage
- `get_current(ch: int = 1)` - Read set current
- `measure_voltage(ch: int = 1)` - Measure actual output voltage
- `measure_current(ch: int = 1)` - Measure actual output current

**Example**: Set voltage to 3.3V
```bash
curl -X POST http://localhost:57666/api/call \
  -H "Content-Type: application/json" \
  -d '{"device_id":"psu-1","method":"set_voltage","args":[3.3]}'
```

### Digital Multimeter (DMM)

**Available Methods**:

- `identify()` - Get device identification
- `poll_status()` - Get current measurement
- `measure()` - Take a measurement
- `set_mode(mode: str)` - Set measurement mode (voltage, current, resistance, etc.)
- `get_mode()` - Get current measurement mode

**Example**: Read current measurement
```bash
curl http://localhost:57666/instruments | jq '.[] | select(.id=="dmm-1") | .status'
```

### Electronic Load (ELL)

**Available Methods**:

- `identify()` - Get device identification
- `poll_status()` - Get current load status
- `set_mode(mode: str)` - Set load mode (CC, CV, CR, CP)
- `set_current(current: float)` - Set constant current
- `set_voltage(voltage: float)` - Set constant voltage
- `set_resistance(resistance: float)` - Set constant resistance
- `set_power(power: float)` - Set constant power
- `set_input(state: bool)` - Enable/disable load input

**Example**: Set load to 1A constant current
```bash
curl -X POST http://localhost:57666/api/call \
  -H "Content-Type: application/json" \
  -d '{"device_id":"load-1","method":"set_mode","args":["CC"]}'

curl -X POST http://localhost:57666/api/call \
  -H "Content-Type: application/json" \
  -d '{"device_id":"load-1","method":"set_current","args":[1.0]}'
```

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Device or method not found
- `500` - Internal server error

**Error Response Format**:
```json
{
  "detail": "Device 'psu-999' not found"
}
```

## Rate Limiting

No rate limiting is currently enforced. However, for optimal performance:

- Limit polling to 1-2 Hz per device
- Use WebSocket for real-time updates instead of polling
- Batch operations when possible

## CORS

CORS is enabled for all origins to support browser-based clients.

## API Versioning

The API is currently unversioned. Breaking changes will be documented in release notes.

## Code Examples

### Python

```python
import requests

API_BASE = "http://localhost:57666"

# Get all instruments
instruments = requests.get(f"{API_BASE}/instruments").json()
print(instruments)

# Set PSU voltage
response = requests.post(f"{API_BASE}/api/call", json={
    "device_id": "psu-1",
    "method": "set_voltage",
    "args": [5.0]
})
print(response.json())

# WebSocket connection
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(data)

ws = websocket.WebSocketApp(
    "ws://localhost:57666/ws/registry",
    on_message=on_message
)
ws.run_forever()
```

### JavaScript

```javascript
// Fetch instruments
const instruments = await fetch('http://localhost:57666/instruments')
  .then(r => r.json());
console.log(instruments);

// Call method
const result = await fetch('http://localhost:57666/api/call', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    device_id: 'psu-1',
    method: 'set_voltage',
    args: [5.0]
  })
}).then(r => r.json());
console.log(result);

// WebSocket connection
const ws = new WebSocket('ws://localhost:57666/ws/registry');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

### curl

```bash
# Get instruments
curl http://localhost:57666/instruments | jq

# Call method
curl -X POST http://localhost:57666/api/call \
  -H "Content-Type: application/json" \
  -d '{"device_id":"psu-1","method":"set_voltage","args":[5.0]}'

# Health check
curl http://localhost:57666/status
```

## Driver CLI Tool

For quick testing of driver methods from command line:

```bash
# List devices
python -m benchmesh_service.tools.driver_cli list \
  --config benchmesh-serial-service/config.yaml

# List available methods
python -m benchmesh_service.tools.driver_cli methods \
  --id psu-1 \
  --config benchmesh-serial-service/config.yaml

# Call a method
python -m benchmesh_service.tools.driver_cli call \
  --id psu-1 \
  --method set_voltage \
  5.0 \
  --config benchmesh-serial-service/config.yaml
```

## Further Documentation

For detailed, interactive API documentation with request/response examples and the ability to test endpoints directly, use the **Swagger UI** embedded above or visit http://localhost:57666/docs.
