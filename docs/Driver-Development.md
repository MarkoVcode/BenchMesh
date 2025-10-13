# Driver Development Guide

This guide walks you through creating a new driver for BenchMesh, from initial setup to testing and deployment.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Driver Architecture](#driver-architecture)
- [Step-by-Step Guide](#step-by-step-guide)
- [Naming Conventions](#naming-conventions)
- [Manifest Configuration](#manifest-configuration)
- [Testing Your Driver](#testing-your-driver)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Debugging](#debugging)

## Overview

A BenchMesh driver is a Python module that:
- Communicates with a specific device via serial protocol
- Exposes standardized methods for identification and status polling
- Provides device-specific control methods
- Includes a manifest describing supported models and configuration

## Prerequisites

Before creating a driver, ensure you have:

1. **Device documentation** - Serial command reference manual
2. **Physical access** - The device connected for testing
3. **Serial parameters** - Baud rate, data bits, parity, stop bits
4. **Protocol knowledge** - Command format, response format, EOL characters
5. **Development environment** - Python 3.8+, test dependencies installed

## Driver Architecture

Each driver consists of three main components:

```
drivers/my_device/
├── __init__.py          # Package initialization (can be empty)
├── driver.py            # Driver implementation class
└── manifest.json        # Device models, classes, and configuration
```

### Driver Class Structure

```python
from ...transport import SerialTransport

class MyDeviceDriver:
    def __init__(self, port, baudrate=9600, serial_mode='8N1', seol='\r\n', reol='\r\n'):
        """
        Initialize driver with serial connection.

        Args:
            port: Serial port path (e.g., '/dev/ttyUSB0')
            baudrate: Communication speed
            serial_mode: Format like '8N1' (data bits, parity, stop bits)
            seol: Send end-of-line character(s)
            reol: Receive end-of-line character(s)
        """
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode,
                                seol=seol, reol=reol).open()

    def query_identify(self):
        """
        REQUIRED: Get device identification string.
        Usually implements the standard SCPI *IDN? command.

        Returns:
            str: Device identification (manufacturer, model, serial, firmware)
        """
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int = 1):
        """
        REQUIRED: Get current device status for periodic polling.
        Called every ~2 seconds by the SerialManager.

        Args:
            channel: Device channel number (if multi-channel)

        Returns:
            dict: Status information as JSON-serializable dictionary
        """
        return {
            "voltage": self.query_output_voltage(channel),
            "current": self.query_output_current(channel),
            "output": self.query_output_state(channel)
        }

    # Device-specific methods following naming convention
    def query_output_voltage(self, channel: int):
        """Query the actual output voltage."""
        self.t.write_line(f'VOUT{channel}?')
        return self.t.read_until_reol(1024)

    def set_voltage(self, channel: int, value: float):
        """Set the voltage setpoint."""
        self.t.write_line(f'VSET{channel}:{value}')
        return self.t.read_until_reol(1024)
```

## Step-by-Step Guide

### Step 1: Create Driver Package

```bash
cd benchmesh-serial-service/src/benchmesh_service/drivers
mkdir my_device
touch my_device/__init__.py
touch my_device/driver.py
touch my_device/manifest.json
```

### Step 2: Implement Required Methods

Edit `driver.py` and implement the two required methods:

```python
from ...transport import SerialTransport

class MyDeviceDriver:
    def __init__(self, port, baudrate=9600, serial_mode='8N1', seol='\r\n', reol='\r\n'):
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode,
                                seol=seol, reol=reol).open()

    def query_identify(self):
        """Get device identification - REQUIRED"""
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int = 1):
        """Get device status - REQUIRED"""
        # Return device status as a dictionary
        return {
            "connected": True,
            "status": "operational"
        }
```

### Step 3: Add Device-Specific Methods

Follow the **naming convention** for methods:

- **Query methods** (read): Prefix with `query_`
- **Setter methods** (write): Prefix with `set_`

```python
    # Query methods (read operations)
    def query_voltage(self, channel: int):
        """Read voltage setpoint."""
        self.t.write_line(f'VSET{channel}?')
        return self._parse_float(self.t.read_until_reol(1024))

    def query_output_voltage(self, channel: int):
        """Read actual output voltage."""
        self.t.write_line(f'VOUT{channel}?')
        return self._parse_float(self.t.read_until_reol(1024))

    def query_current(self, channel: int):
        """Read current setpoint."""
        self.t.write_line(f'ISET{channel}?')
        return self._parse_float(self.t.read_until_reol(1024))

    def query_output_state(self, channel: int):
        """Check if output is enabled."""
        self.t.write_line(f'OUT{channel}?')
        response = self.t.read_until_reol(1024)
        return response.strip() == '1'

    # Setter methods (write operations)
    def set_voltage(self, channel: int, value: float):
        """Set voltage setpoint."""
        self.t.write_line(f'VSET{channel}:{value}')
        return self.t.read_until_reol(1024)

    def set_current(self, channel: int, value: float):
        """Set current limit."""
        self.t.write_line(f'ISET{channel}:{value}')
        return self.t.read_until_reol(1024)

    def set_output(self, channel: int, enabled: bool):
        """Enable or disable output."""
        state = '1' if enabled else '0'
        self.t.write_line(f'OUT{channel}:{state}')
        return self.t.read_until_reol(1024)

    # Helper methods (private, prefix with _)
    def _parse_float(self, response: str):
        """Parse numeric response."""
        try:
            return float(response.strip())
        except (ValueError, AttributeError):
            return None
```

### Step 4: Create Manifest

Create `manifest.json` describing your device:

```json
{
  "$schema": "benchmesh.schema.instrument.profile.v1.json",
  "vendor": "ACME",
  "family": "PowerPro",
  "version": "1.0.0",
  "models": {
    "PP-3000": {
      "id_patterns": [
        "ACME PowerPro 3000"
      ],
      "classes": [
        "PSU"
      ],
      "connection": {
        "seol": "\r\n",
        "reol": "\r\n",
        "def_conn_ver_command": "*IDN?"
      },
      "instrument_class": {
        "PSU": {
          "pooling": [
            {
              "method": "poll_status",
              "interval": 2.0
            }
          ],
          "ui_component": "GenericPSU",
          "features": {
            "channels": 1,
            "absolute_limits": {
              "voltage": {
                "unit": "V",
                "max": 30.0
              },
              "current": {
                "unit": "A",
                "max": 3.0
              },
              "power": {
                "unit": "W",
                "max": 90.0
              }
            }
          }
        }
      }
    }
  }
}
```

### Step 5: Add Device to Configuration

Edit `config.yaml` to add your device:

```yaml
version: 1
devices:
  - id: my-device-1
    name: "ACME Power Supply"
    driver: my_device
    port: /dev/ttyUSB0
    baud: 9600
    serial: 8N1
    model: PP-3000
```

### Step 6: Test Your Driver

Use the driver CLI tool to test methods:

```bash
# Set PYTHONPATH if needed
export PYTHONPATH=benchmesh-serial-service/src

# List available methods
python -m benchmesh_service.tools.driver_cli methods \
    --id my-device-1 --config config.yaml

# Test identification
python -m benchmesh_service.tools.driver_cli call \
    --id my-device-1 --method query_identify --config config.yaml

# Test status polling
python -m benchmesh_service.tools.driver_cli call \
    --id my-device-1 --method poll_status --config config.yaml

# Test setting voltage
python -m benchmesh_service.tools.driver_cli call \
    --id my-device-1 --method set_voltage 12.0 --config config.yaml
```

## Naming Conventions

### Method Naming (CRITICAL)

The API relies on method prefixes for security and routing:

| Type | Prefix | HTTP Verb | Example |
|------|--------|-----------|---------|
| Read operations | `query_` | GET | `query_voltage()` |
| Write operations | `set_` | POST | `set_voltage()` |
| Internal helpers | `_` | N/A | `_parse_float()` |

**Examples**:
```python
# GOOD - Will work with API
def query_voltage(self, channel: int):
    """Read voltage setpoint"""

def set_voltage(self, channel: int, value: float):
    """Set voltage setpoint"""

# BAD - Will NOT work with API
def get_voltage(self, channel: int):  # Wrong prefix

def voltage(self, channel: int):  # No prefix
```

**API Mapping**:
```
GET  /instruments/PSU/device-1/1/voltage     → query_voltage(1)
POST /instruments/PSU/device-1/1/voltage/12.5 → set_voltage(1, 12.5)
GET  /instruments/PSU/device-1/1/current     → query_current(1)
POST /instruments/PSU/device-1/1/output/true  → set_output(1, true)
```

### Variable Naming

- Use descriptive names: `voltage_setpoint` not `v`
- Channel parameter: Always use `channel: int`
- Boolean parameters: Use `enabled`, `active`, not `flag`

## Manifest Configuration

### Basic Structure

```json
{
  "$schema": "benchmesh.schema.instrument.profile.v1.json",
  "vendor": "MANUFACTURER_NAME",
  "family": "DEVICE_FAMILY",
  "version": "1.0.0",
  "models": { ... },
}
```

### Models Section

Define each supported model:

```json
"models": {
  "MODEL-NUMBER": {
    "id_patterns": [
      "Expected *IDN? response pattern"
    ],
    "classes": ["PSU"],  // Device class (PSU, DMM, AWG, OSC, etc.)
    "connection": {
      "seol": "\r\n",              // Send end-of-line
      "reol": "\r\n",              // Receive end-of-line
      "def_conn_ver_command": "*IDN?"  // Identification command
    },
    "instrument_class": { ... }
  }
}
```

### Device Classes

Available device classes:

- `PSU` - Power Supply
- `DMM` - Digital Multimeter
- `AWG` - Arbitrary Waveform Generator / Function Generator
- `OSC` - Oscilloscope
- `SAL` - Spectrum Analyzer
- `ELL` - Electronic Load
- `LCR` - LCR Meter

To add new classes, edit `drivers/classes.json`.

### Polling Configuration

```json
"instrument_class": {
  "PSU": {
    "pooling": [
      {
        "method": "poll_status",
        "interval": 2.0  // Seconds between calls
      }
    ],
    "ui_component": "GenericPSU",
    "features": { ... }
  }
}
```

### Features Section

Define device capabilities and limits:

```json
"features": {
  "lock": true,           // Supports front-panel lock
  "channels": 2,          // Number of channels
  "memory_banks": 5,      // Preset memory slots
  "absolute_limits": {
    "voltage": {
      "unit": "V",
      "max": 30.0
    },
    "current": {
      "unit": "A",
      "max": 5.0
    },
    "power": {
      "unit": "W",
      "max": 150.0
    }
  }
}
```

## Testing Your Driver

### Unit Tests

Create `tests/test_my_device.py`:

```python
import pytest
from unittest.mock import Mock
from benchmesh_service.drivers.my_device.driver import MyDeviceDriver

@pytest.fixture
def mock_transport():
    """Create a mock SerialTransport."""
    transport = Mock()
    transport.open.return_value = transport
    return transport

@pytest.fixture
def driver(mock_transport, monkeypatch):
    """Create driver with mocked transport."""
    def mock_serial_transport(*args, **kwargs):
        return mock_transport

    monkeypatch.setattr(
        'benchmesh_service.drivers.my_device.driver.SerialTransport',
        mock_serial_transport
    )

    return MyDeviceDriver(port='/dev/ttyUSB0', baudrate=9600)

def test_identify(driver, mock_transport):
    """Test device identification."""
    mock_transport.read_until_reol.return_value = "ACME PowerPro 3000 v1.0"

    result = driver.query_identify()

    mock_transport.write_line.assert_called_with('*IDN?')
    assert "ACME" in result
    assert "PowerPro" in result

def test_set_voltage(driver, mock_transport):
    """Test setting voltage."""
    mock_transport.read_until_reol.return_value = "OK"

    result = driver.set_voltage(1, 12.5)

    mock_transport.write_line.assert_called_with('VSET1:12.5')
    assert result == "OK"

def test_poll_status(driver, mock_transport):
    """Test status polling."""
    mock_transport.read_until_reol.side_effect = ["12.0", "1.5", "1"]

    status = driver.poll_status(1)

    assert "voltage" in status
    assert "current" in status
```

### Integration Tests

Test with real hardware:

```python
@pytest.mark.integration
def test_real_device_connection():
    """Test connection to real device."""
    driver = MyDeviceDriver(port='/dev/ttyUSB0', baudrate=9600)

    # Test identification
    idn = driver.query_identify()
    assert "ACME" in idn

    # Test status
    status = driver.poll_status(1)
    assert "voltage" in status
```

Run integration tests separately:

```bash
# Skip integration tests (default for CI)
pytest benchmesh-serial-service/tests

# Run integration tests only
pytest -m integration benchmesh-serial-service/tests
```

## Best Practices

### 1. Error Handling

```python
def query_voltage(self, channel: int):
    """Read voltage with error handling."""
    try:
        self.t.write_line(f'VSET{channel}?')
        response = self.t.read_until_reol(1024)
        return self._parse_float(response)
    except Exception as e:
        # Let the error propagate - SerialManager handles reconnection
        raise RuntimeError(f"Failed to query voltage on channel {channel}: {e}")
```

### 2. Response Parsing

```python
def _parse_float(self, response: str):
    """Safely parse float from device response."""
    if not response:
        return None
    try:
        # Strip whitespace and units
        clean = response.strip().rstrip('V').rstrip('A').strip()
        return float(clean)
    except (ValueError, AttributeError):
        return None

def _parse_bool(self, response: str):
    """Parse boolean response."""
    clean = response.strip().lower()
    return clean in ('1', 'on', 'true', 'yes')
```

### 3. Channel Handling

```python
def _validate_channel(self, channel: int):
    """Validate channel number."""
    if not 1 <= channel <= self.num_channels:
        raise ValueError(f"Invalid channel {channel}, must be 1-{self.num_channels}")

def set_voltage(self, channel: int, value: float):
    """Set voltage with validation."""
    self._validate_channel(channel)
    self.t.write_line(f'VSET{channel}:{value}')
    return self.t.read_until_reol(1024)
```

### 4. Binary Protocols

Some devices use binary protocols instead of ASCII:

```python
def query_status(self, channel: int):
    """Query binary status response."""
    self.t.write_line('STATUS?')
    data = self.t.read(8)  # Read exactly 8 bytes

    if not data or len(data) < 1:
        return {}

    status_byte = data[0]

    return {
        "mode": "CV" if (status_byte & 0x01) else "CC",
        "output": bool(status_byte & 0x40),
        "lock": bool(status_byte & 0x20)
    }
```

### 5. Timeouts and Delays

```python
import time

def set_voltage(self, channel: int, value: float):
    """Set voltage with settling delay."""
    self.t.write_line(f'VSET{channel}:{value}')
    response = self.t.read_until_reol(1024)

    # Some devices need time to apply settings
    time.sleep(0.1)

    return response
```

## Common Patterns

### Multi-Channel Devices

```python
class MultiChannelDriver:
    def __init__(self, port, baudrate, serial_mode='8N1', seol='\r\n', reol='\r\n'):
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode,
                                seol=seol, reol=reol).open()
        self.num_channels = 2

    def poll_status(self, channel: int = None):
        """Poll all channels or specific channel."""
        if channel is not None:
            return self._poll_single_channel(channel)

        # Poll all channels
        return {
            f"ch{ch}": self._poll_single_channel(ch)
            for ch in range(1, self.num_channels + 1)
        }

    def _poll_single_channel(self, channel: int):
        """Poll single channel status."""
        return {
            "voltage": self.query_output_voltage(channel),
            "current": self.query_output_current(channel)
        }
```

### Devices with Operating Modes

```python
def query_mode(self, channel: int):
    """Query operating mode (CV/CC)."""
    self.t.write_line(f'MODE{channel}?')
    response = self.t.read_until_reol(1024).strip()
    return response  # "CV", "CC", etc.

def set_mode(self, channel: int, mode: str):
    """Set operating mode."""
    if mode not in ['CV', 'CC', 'CR']:
        raise ValueError(f"Invalid mode: {mode}")

    self.t.write_line(f'MODE{channel}:{mode}')
    return self.t.read_until_reol(1024)
```

### Devices Requiring Unlocking

```python
def set_lock(self, enabled: bool):
    """Lock/unlock front panel."""
    state = '1' if enabled else '0'
    self.t.write_line(f'LOCK:{state}')
    return self.t.read_until_reol(1024)
```

## Debugging

### Enable Verbose Logging

Add logging to your driver:

```python
import logging

logger = logging.getLogger(__name__)

class MyDeviceDriver:
    def query_voltage(self, channel: int):
        logger.debug(f"Querying voltage for channel {channel}")
        self.t.write_line(f'VSET{channel}?')
        response = self.t.read_until_reol(1024)
        logger.debug(f"Voltage response: {response}")
        return self._parse_float(response)
```

Run with debug logging:

```bash
PYTHONPATH=benchmesh-serial-service/src python -m benchmesh_service.main \
    --config config.yaml --log-level DEBUG
```

### Test Transport Directly

```python
from benchmesh_service.transport import SerialTransport

# Open connection
t = SerialTransport('/dev/ttyUSB0', 9600, seol='\r\n', reol='\r\n').open()

# Send command
t.write_line('*IDN?')

# Read response
print(t.read_until_reol(1024))

# Close
t.close()
```

### Use Driver CLI

```bash
# Test specific method with arguments
python -m benchmesh_service.tools.driver_cli call \
    --id my-device-1 \
    --method set_voltage \
    --config config.yaml \
    12.5

# Use kwargs for complex calls
python -m benchmesh_service.tools.driver_cli call \
    --id my-device-1 \
    --method set_mode \
    --config config.yaml \
    --kwargs '{"channel":1, "mode":"CV"}'
```

## Checklist

Before submitting your driver:

- [ ] Implemented `query_identify()` method
- [ ] Implemented `poll_status()` method
- [ ] All methods follow naming convention (`query_*`, `set_*`)
- [ ] Created complete `manifest.json`
- [ ] Added device to `config.yaml` for testing
- [ ] Wrote unit tests with mocked transport
- [ ] Tested with real hardware
- [ ] Added docstrings to all public methods
- [ ] Error handling in place
- [ ] Driver works via CLI tool
- [ ] Driver works via API endpoints
- [ ] Driver works in UI
- [ ] Updated documentation

## Related Documentation

- [Architecture](Architecture) - System architecture overview
- [Configuration](Configuration) - Config file format
- [API Reference](API-Reference) - API endpoint details
- [Testing](Testing) - Running and writing tests
- [Contributing](../CONTRIBUTING.md) - Contribution guidelines
