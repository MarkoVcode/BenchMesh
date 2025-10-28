# Driver Development Guide

This guide explains how to create new instrument drivers for BenchMesh using the DriverBase architecture.

## Table of Contents

- [Quick Start](#quick-start)
- [DriverBase Architecture](#driverbase-architecture)
- [Creating a New Driver](#creating-a-new-driver)
- [Built-in Features](#built-in-features)
- [Best Practices](#best-practices)
- [Testing](#testing)
- [Examples](#examples)

## Quick Start

A minimal driver requires just 3 things:

```python
from ..base import DriverBase

class MyDriver(DriverBase):
    def query_identify(self) -> str:
        """Return device identification string (*IDN? command)."""
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int) -> dict:
        """Poll device status for periodic updates."""
        self.t.write_line('MEAS:ALL?')
        raw = self.t.read_until_reol(1024)
        return {"STATUS": raw}
```

That's it! No constructor needed, caching is automatic, all common methods are inherited.

## DriverBase Architecture

All drivers inherit from `DriverBase`, which provides:

### Automatic Setup
- **Transport management**: `self.t` automatically configured
- **Caching**: `self.cache` (SimpleCache) automatically created
- **No constructor needed**: DriverBase handles initialization

### Inherited Methods
- `close()` - Close transport and cleanup
- `is_connected()` - Check if transport is open
- `set_reset()` - Reset device with USB TMC auto-detection
- `write()`, `read()`, `write_line()`, `read_until_reol()` - Transport delegation

### Helper Methods
- `_parse_numeric(s)` - Extract float from device response
- `_clean_response(raw)` - Normalize bytes/str response
- `_is_usb_tmc()` - Detect USB TMC transport

### Abstract Methods (Must Implement)
- `query_identify()` - Return device identification
- `poll_status(channel)` - Return device status dict

## Creating a New Driver

### 1. Create Driver Package

```bash
mkdir -p src/benchmesh_service/drivers/my_device
touch src/benchmesh_service/drivers/my_device/__init__.py
touch src/benchmesh_service/drivers/my_device/driver.py
```

### 2. Implement Driver Class

```python
# src/benchmesh_service/drivers/my_device/driver.py
from ..base import DriverBase

class MyDevice(DriverBase):
    # Required: Implement abstract methods
    def query_identify(self) -> str:
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int) -> dict:
        # Use cache to minimize redundant queries
        voltage = self.cache.get_or_set("voltage", self.query_voltage, channel)
        current = self.cache.get_or_set("current", self.query_current, channel)

        return {
            "VOLTAGE": voltage,
            "CURRENT": current
        }

    # Device-specific query methods (read)
    def query_voltage(self, channel: int) -> str:
        self.t.write_line(f'MEAS:VOLT? CH{channel}')
        return self.t.read_until_reol(1024)

    def query_current(self, channel: int) -> str:
        self.t.write_line(f'MEAS:CURR? CH{channel}')
        return self.t.read_until_reol(1024)

    # Device-specific set methods (write)
    def set_voltage(self, channel: int, value: float) -> str:
        self.t.write_line(f'VOLT {value}')
        response = self.t.read_until_reol(1024)

        # Invalidate cache when device state changes
        self.cache.invalidate("voltage")

        return response

    def set_current(self, channel: int, value: float) -> str:
        self.t.write_line(f'CURR {value}')
        response = self.t.read_until_reol(1024)

        # Invalidate cache when device state changes
        self.cache.invalidate("current")

        return response
```

### 3. Create Manifest

```json
{
  "vendor": "MyVendor",
  "family": "MyDevice",
  "version": "1.0.0",
  "models": {
    "MyDevice-1000": {
      "name": "MyDevice 1000 Series",
      "classes": ["PSU"]
    }
  },
  "polling": {
    "PSU": {
      "method": "poll_status",
      "interval": 2.0
    }
  },
  "connection": {
    "send_eol": "\r",
    "recv_eol": "\r"
  },
  "supported_transports": ["serial"]
}
```

### 4. Write Tests

```python
# tests/test_my_device.py
from unittest.mock import Mock
from benchmesh_service.drivers.my_device.driver import MyDevice

def test_query_identify():
    transport = Mock()
    transport.is_open = True
    transport.read_until_reol.return_value = "MyVendor,MyDevice-1000,1.0"

    driver = MyDevice(transport=transport)
    result = driver.query_identify()

    assert "MyVendor" in result
    transport.write_line.assert_called_once_with('*IDN?')

def test_poll_status_uses_cache():
    transport = Mock()
    transport.is_open = True
    transport.read_until_reol.side_effect = ["12.5", "1.2"]

    driver = MyDevice(transport=transport)

    # First poll - queries device
    result1 = driver.poll_status(1)
    assert result1["VOLTAGE"] == "12.5"
    assert transport.write_line.call_count == 2  # voltage + current

    # Second poll - uses cache
    transport.write_line.reset_mock()
    result2 = driver.poll_status(1)
    assert result2["VOLTAGE"] == "12.5"
    assert transport.write_line.call_count == 0  # cached!
```

## Built-in Features

### Caching

Every driver has `self.cache` available:

```python
def poll_status(self, channel: int) -> dict:
    # Lazy cache population with get_or_set
    voltage = self.cache.get_or_set("voltage", self.query_voltage, channel)

    # Manual cache management
    cached = self.cache.get("mode")
    if cached is None:
        cached = self.query_mode(channel)
        self.cache.set("mode", cached)

    return {"VOLTAGE": voltage, "MODE": cached}

def set_voltage(self, channel: int, value: float):
    self.t.write_line(f'VOLT {value}')
    result = self.t.read_until_reol(1024)

    # Invalidate cache when state changes
    self.cache.invalidate("voltage")

    return result
```

**Cache Benefits:**
- 3x speedup in polling (measured with owon_oel)
- Reduces SCPI calls between polling and API requests
- Thread-safe by default
- No TTL (values persist until invalidated)

### USB TMC Auto-Detection

USB TMC devices don't respond to SET commands. DriverBase handles this automatically:

```python
# No override needed - DriverBase handles both Serial and USB TMC:
def set_reset(self) -> Optional[str]:
    self.t.write_line('*RST')

    # USB TMC: returns None (no read)
    # Serial: returns response (reads 1024 bytes)
    if self._is_usb_tmc():
        return None
    return self.t.read_until_reol(1024)
```

You can override `set_reset()` for non-standard behavior, but most drivers don't need to.

### Helper Methods

```python
def poll_status(self, channel: int) -> dict:
    # Extract numeric values from device responses
    raw_voltage = self.query_voltage(channel)
    voltage = self._parse_numeric(raw_voltage)  # "12.5V" → 12.5

    # Clean string responses
    raw_mode = self.query_mode(channel)
    mode = self._clean_response(raw_mode)  # b'"VOLT"\r' → "VOLT"

    return {
        "VOLTAGE": voltage,
        "MODE": mode
    }
```

## Best Practices

### 1. Follow Naming Conventions

- **Query methods** (read): `query_*` - e.g., `query_voltage()`, `query_current()`
- **Set methods** (write): `set_*` - e.g., `set_voltage()`, `set_current()`

This enables API smart resolution:
- `GET /instruments/PSU/device-1/1/voltage` → `query_voltage(1)`
- `POST /instruments/PSU/device-1/1/voltage/12.5` → `set_voltage(1, 12.5)`

### 2. Use Caching for Slow-Changing Values

Cache values that rarely change (like mode, input enable):

```python
def poll_status(self, channel: int) -> dict:
    # Slow-changing: cache it
    mode = self.cache.get_or_set("mode", self.query_mode, channel)

    # Fast-changing: always query
    voltage = self.query_voltage(channel)

    return {"MODE": mode, "VOLTAGE": voltage}
```

### 3. Invalidate Cache on State Changes

```python
def set_mode(self, channel: int, value: str):
    self.t.write_line(f'MODE {value}')
    result = self.t.read_until_reol(1024)

    # Important: invalidate so next poll queries new value
    self.cache.invalidate("mode")

    return result
```

### 4. Handle Multi-Class Devices

Some devices expose multiple instrument classes (e.g., PSU + DMM):

```python
def poll_status(self, channel: int) -> dict:
    """Return nested dict for multi-class device."""
    psu_data = self._poll_psu(channel)
    dmm_data = self._poll_dmm(channel)

    return {
        "PSU": psu_data,
        "DMM": dmm_data
    }
```

### 5. Use Type Hints

```python
from typing import Dict, Any, Optional

def poll_status(self, channel: int) -> Dict[str, Any]:
    """Poll device status."""
    ...

def query_voltage(self, channel: int) -> str:
    """Query voltage reading."""
    ...

def set_voltage(self, channel: int, value: float) -> Optional[str]:
    """Set voltage setpoint."""
    ...
```

## Testing

### Unit Tests

Test driver methods with mocked transport:

```python
from unittest.mock import Mock
import pytest

@pytest.fixture
def mock_transport():
    transport = Mock()
    transport.is_open = True
    transport.write_line = Mock()
    transport.read_until_reol = Mock(return_value="OK")
    return transport

@pytest.fixture
def driver(mock_transport):
    return MyDevice(transport=mock_transport)

def test_query_voltage(driver, mock_transport):
    mock_transport.read_until_reol.return_value = "12.5"

    result = driver.query_voltage(1)

    assert result == "12.5"
    mock_transport.write_line.assert_called_with('MEAS:VOLT? CH1')
```

### Integration Tests

Test with real serial communication:

```python
@pytest.mark.integration
def test_real_device():
    from benchmesh_service.transport import SerialTransport

    transport = SerialTransport('/dev/ttyUSB0', 115200,
                               serial_mode='8N1',
                               seol='\r', reol='\r').open()

    driver = MyDevice(transport=transport)

    idn = driver.query_identify()
    assert "MyVendor" in idn

    driver.close()
```

## Examples

### Minimal Driver (DMM)

```python
from ..base import DriverBase

class SimpleDMM(DriverBase):
    def query_identify(self) -> str:
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int) -> dict:
        self.t.write_line('MEAS?')
        measurement = self.t.read_until_reol(1024)
        return {"MEASUREMENT": self._parse_numeric(measurement)}
```

### Power Supply with Caching

```python
from ..base import DriverBase

class CachedPSU(DriverBase):
    def query_identify(self) -> str:
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int) -> dict:
        # Cache slow-changing values
        output_enabled = self.cache.get_or_set("output",
                                              self.query_output, channel)

        # Always query fast-changing values
        voltage = self._parse_numeric(self.query_voltage(channel))
        current = self._parse_numeric(self.query_current(channel))

        return {
            "OUTPUT": output_enabled,
            "VOLTAGE": voltage,
            "CURRENT": current
        }

    def query_output(self, channel: int) -> str:
        self.t.write_line('OUTP?')
        return self.t.read_until_reol(1024)

    def query_voltage(self, channel: int) -> str:
        self.t.write_line('MEAS:VOLT?')
        return self.t.read_until_reol(1024)

    def query_current(self, channel: int) -> str:
        self.t.write_line('MEAS:CURR?')
        return self.t.read_until_reol(1024)

    def set_output(self, channel: int, state: str):
        self.t.write_line(f'OUTP {state}')
        result = self.t.read_until_reol(1024)
        self.cache.invalidate("output")  # Important!
        return result
```

### Multi-Class Device (PSU + DMM)

```python
from ..base import DriverBase

class MultiDevice(DriverBase):
    def query_identify(self) -> str:
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int) -> dict:
        """Return nested dict with class-specific data."""
        return {
            "PSU": self._poll_psu(channel),
            "DMM": self._poll_dmm(channel)
        }

    def _poll_psu(self, channel: int) -> dict:
        self.t.write_line('PSU:MEAS?')
        raw = self.t.read_until_reol(1024)
        parts = raw.split(',')
        return {
            "VOLTAGE": self._parse_numeric(parts[0]),
            "CURRENT": self._parse_numeric(parts[1])
        }

    def _poll_dmm(self, channel: int) -> dict:
        self.t.write_line('DMM:MEAS?')
        measurement = self.t.read_until_reol(1024)
        return {
            "MEASUREMENT": self._parse_numeric(measurement)
        }
```

## Reference Implementations

See these drivers for real-world examples:

- **Simple DMM**: `owon_xdm/driver.py` - Basic queries, minimal caching
- **Cached PSU**: `owon_oel/driver.py` - Heavy cache usage, get_or_set pattern
- **Multi-class**: `owon_spm/driver.py` - PSU + DMM in one device
- **Complex**: `rigol_dho800/driver.py` - Oscilloscope with binary data
- **Binary Protocol**: `tenma_72/driver.py` - STATUS? returns binary byte

## Additional Resources

- **DriverBase API**: See `drivers/base.py` source code
- **Transport Layer**: See `transport/` for SerialTransport and UsbTmcTransport
- **Caching Guide**: See `CACHE_DESIGN.md` for comprehensive caching documentation
- **Main Documentation**: See root `CLAUDE.md` for architecture overview
