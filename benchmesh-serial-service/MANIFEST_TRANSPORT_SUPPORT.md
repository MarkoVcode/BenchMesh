# Manifest Transport Support Schema

This document defines how driver manifests specify which physical transports they support.

## Overview

Drivers can support multiple transport types (Serial, USB TMC, TCP/IP). The manifest declares which transports are compatible with the instrument, enabling the Configuration UI to show appropriate connection options.

## Manifest Field: `supported_transports`

Add this **top-level field** to your driver's `manifest.json`:

```json
{
  "$schema": "benchmesh.schema.instrument.profile.v1.json",
  "vendor": "OWON",
  "family": "XDM",
  "version": "1.0.0",
  "supported_transports": ["serial", "usbtmc"],
  "models": {
    ...
  }
}
```

### Transport Types

| Transport | Description | Typical Use Case |
|-----------|-------------|------------------|
| `"serial"` | RS232/USB-Serial | Legacy instruments, USB-Serial adapters (FTDI, Prolific) |
| `"usbtmc"` | USB Test & Measurement Class | Modern USB instruments (IEEE 488.2 over USB) |
| `"tcpip"` | TCP/IP sockets | LXI instruments, SCPI-over-TCP, networked devices |

### Default Behavior

If `supported_transports` is **not specified**, the driver defaults to `["serial"]` for backward compatibility.

### Examples

**1. Serial-only driver (legacy instrument):**
```json
{
  "vendor": "TENMA",
  "family": "72",
  "supported_transports": ["serial"]
}
```

**2. USB TMC-only driver (modern USB instrument):**
```json
{
  "vendor": "RIGOL",
  "family": "DS1000Z",
  "supported_transports": ["usbtmc"]
}
```

**3. Multi-transport driver (hybrid support):**
```json
{
  "vendor": "OWON",
  "family": "XDM",
  "supported_transports": ["serial", "usbtmc"],
  "models": {
    "XDM1241": {
      "id_patterns": ["OWON,XDM1241"],
      "transport_hints": {
        "serial": {
          "note": "Requires RS232 adapter cable"
        },
        "usbtmc": {
          "preferred": true,
          "note": "Direct USB connection (recommended)"
        }
      }
    }
  }
}
```

**4. Network-capable driver:**
```json
{
  "vendor": "KEYSIGHT",
  "family": "DSO-X",
  "supported_transports": ["usbtmc", "tcpip"],
  "models": {
    "DSOX1204G": {
      "transport_hints": {
        "tcpip": {
          "default_port": 5025,
          "note": "LXI/VXI-11 protocol"
        }
      }
    }
  }
}
```

## Configuration UI Behavior

The Configuration UI uses `supported_transports` to:

1. **Filter transport options**: Only show transports the driver supports
2. **Render appropriate forms**: Different fields for Serial vs USB TMC vs TCP/IP
3. **Filter device lists**:
   - Serial transport → show `/dev/ttyUSB*`, `COM*` devices
   - USB TMC transport → show USB TMC devices (e.g., `/dev/usbtmc0`)
   - TCP/IP transport → show hostname/IP input field

### Transport-Specific Configuration Fields

**Serial Transport:**
- `port`: Device path (e.g., `/dev/ttyUSB0`, `COM3`)
- `baud`: Baud rate (e.g., 9600, 115200)
- `serial`: Data format (e.g., `8N1`)
- Connection EOL: `seol`, `reol` from manifest

**USB TMC Transport:**
- `usbtmc_device`: TMC device path (e.g., `/dev/usbtmc0`)
- Auto-discovery: List available USB TMC devices by manufacturer/model
- Connection EOL: `seol`, `reol` from manifest

**TCP/IP Transport:**
- `host`: Hostname or IP address
- `port`: TCP port (default: 5025 for SCPI)
- `protocol`: `raw` (sockets) or `vxi11` (VXI-11/LXI)
- Connection EOL: `seol`, `reol` from manifest

## Backend Behavior

The `driver_factory.py` reads `supported_transports` from the manifest and validates that the user's chosen transport is supported before instantiating the driver.

### Transport Instantiation Logic

```python
def create_driver(device_config, manifest):
    transport_type = device_config.get('transport', 'serial')  # Default to serial
    supported = manifest.get('supported_transports', ['serial'])

    if transport_type not in supported:
        raise ValueError(f"Transport '{transport_type}' not supported by this driver. "
                        f"Supported: {supported}")

    if transport_type == 'serial':
        transport = SerialTransport(...)
    elif transport_type == 'usbtmc':
        transport = UsbTmcTransport(...)
    elif transport_type == 'tcpip':
        transport = TcpIpTransport(...)

    return DriverClass(transport=transport)
```

## Migration Guide

### Adding Transport Support to Existing Drivers

**Step 1**: Add `supported_transports` to `manifest.json`

```json
{
  "vendor": "OWON",
  "family": "XDM",
  "supported_transports": ["serial", "usbtmc"],  // Add this line
  "models": { ... }
}
```

**Step 2**: Test with both transports

Drivers that accept a `Transport` interface should work with any transport type without code changes. The driver doesn't need to know whether it's using Serial, USB TMC, or TCP/IP - it just calls `transport.write_line()` and `transport.read_until_reol()`.

**Step 3**: Update documentation

Document any transport-specific quirks in the manifest's `transport_hints` field.

## Validation

The system validates:
1. `supported_transports` is a list of valid transport types
2. User's chosen transport is in the driver's `supported_transports` list
3. Required configuration fields exist for the chosen transport

## See Also

- `transport/base.py` - Transport ABC interface
- `transport/serial.py` - Serial transport implementation
- `transport/usbtmc.py` - USB TMC transport implementation (Phase 2)
- `driver_factory.py` - Transport instantiation logic
- `CLAUDE.md` - Overall architecture documentation
