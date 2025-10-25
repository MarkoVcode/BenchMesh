# Config Schema V2 - Multi-Transport Support

## Overview

Config schema V2 adds support for multiple transport types while maintaining backward compatibility with V1 (serial-only) configs.

## Device Configuration Fields

### Common Fields (All Transports)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique device identifier (e.g., `dmm-1`, `psu-1`) |
| `name` | string | Yes | Human-readable device name |
| `driver` | string | Yes | Driver name (maps to driver folder) |
| `model` | string | No | Specific model override (uses manifest matching if omitted) |
| `transport` | string | No | Transport type: `serial` (default), `usbtmc`, `tcpip` |

### Serial Transport Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `port` | string | Yes | Device path (e.g., `/dev/ttyUSB0`, `COM3`) |
| `baud` | integer | Yes | Baud rate (e.g., `9600`, `115200`) |
| `serial` | string | No | Data format (default: `8N1`) |

### USB TMC Transport Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device` | string | Yes | USB TMC device path (e.g., `/dev/usbtmc0`, `/dev/tmcDGE2070`) |

### TCP/IP Transport Fields (Future)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host` | string | Yes | Hostname or IP address |
| `port` | integer | No | TCP port (default: `5025`) |
| `protocol` | string | No | Protocol: `raw` (default), `vxi11` |

## Example Configurations

### Serial Device (V1 - Backward Compatible)

```yaml
version: 1
devices:
  - id: psu-1
    name: Tenma PSU
    driver: tenma_72
    port: /dev/tty722540
    baud: 9600
    serial: 8N1
    model: 72-2540
```

**Note**: Devices without `transport` field default to `serial` for backward compatibility.

### Serial Device (V2 - Explicit Transport)

```yaml
version: 1
devices:
  - id: psu-1
    name: Tenma PSU
    driver: tenma_72
    transport: serial
    port: /dev/tty722540
    baud: 9600
    serial: 8N1
    model: 72-2540
```

### USB TMC Device

```yaml
version: 1
devices:
  - id: dmm-1
    name: OWON XDM1241
    driver: owon_xdm
    transport: usbtmc
    device: /dev/tmcDGE2070  # or /dev/usbtmc0
    model: XDM1241
```

### TCP/IP Device (Future)

```yaml
version: 1
devices:
  - id: scope-1
    name: Rigol DS1054Z
    driver: rigol_ds1000z
    transport: tcpip
    host: 192.168.1.100
    port: 5025
    protocol: raw
```

### Mixed Transport Configuration

```yaml
version: 1
devices:
  # Serial PSU
  - id: psu-1
    name: Tenma PSU
    driver: tenma_72
    port: /dev/tty722540
    baud: 9600
    serial: 8N1

  # USB TMC DMM
  - id: dmm-1
    name: OWON XDM1241
    driver: owon_xdm
    transport: usbtmc
    device: /dev/usbtmc0

  # Network oscilloscope
  - id: scope-1
    name: Rigol Scope
    driver: rigol_ds1000z
    transport: tcpip
    host: scope.local
    port: 5025
```

## Validation Rules

1. **Transport Support**: The chosen `transport` must be in the driver's `supported_transports` list
2. **Required Fields**: All transport-specific required fields must be present
3. **Mutually Exclusive**: Don't mix transport-specific fields (e.g., `port` + `device`)
4. **Backward Compatibility**: Devices without `transport` field use `serial` transport

## Migration from V1 to V2

**No changes required!** V1 configs continue to work. The `transport: serial` is implied.

To explicitly use V2 format:
1. Add `transport: serial` to existing devices (optional)
2. For new USB TMC devices, use `transport: usbtmc` with `device` field
3. Remove `port`, `baud`, `serial` fields from USB TMC devices

## Implementation Notes

The backend validates:
- Transport type is supported by the driver (from manifest)
- Required fields for the transport type are present
- No conflicting fields from different transports

The Configuration UI:
- Shows transport selector
- Renders appropriate form fields based on selected transport
- Filters device lists by transport type
- Only shows drivers that support the selected transport

## See Also

- `MANIFEST_TRANSPORT_SUPPORT.md` - How drivers declare transport support
- `transport/` - Transport implementation classes
- `driver_factory.py` - Transport instantiation logic
