# Multi-Transport Support Guide

BenchMesh supports multiple physical transport layers for communicating with instruments:
- **Serial (RS232/USB-Serial)**: Traditional serial communication via `/dev/ttyUSB*` or `/dev/tty*` devices
- **USB TMC (Test & Measurement Class)**: Direct USB communication via `/dev/usbtmc*` devices (IEEE 488.2 over USB)
- **TCP/IP**: Network communication (planned for future implementation)

## Configuring Transport Type

The `transport` field in config.yaml determines which communication interface to use:

```yaml
# Serial transport example (default if transport not specified)
- id: psu-1
  name: "TENMA PSU"
  driver: tenma_72
  transport: serial     # Optional - defaults to 'serial'
  port: /dev/ttyUSB0
  baud: 9600
  serial: 8N1
  model: 72-2540

# USB TMC transport example
- id: awg-1
  name: "OWON Function Generator"
  driver: owon_dge
  transport: usbtmc
  device: /dev/usbtmc0   # USB TMC device path
  model: DGE2070
```

## Transport-Specific Configuration Fields

| Transport | Required Fields | Optional Fields |
|-----------|----------------|----------------|
| `serial` | `port`, `baud`, `serial` | `model` |
| `usbtmc` | `device` | `model` |
| `tcpip` | `host`, `port` | `model` (future) |

## USB TMC (USB Test & Measurement Class)

USB TMC provides direct USB communication with modern lab instruments without requiring USB-to-Serial adapters. It implements IEEE 488.2 SCPI protocol over USB.

### Benefits

- Direct USB connection (no USB-to-Serial adapter needed)
- Faster communication than serial
- Auto-discovery of connected USB TMC devices
- Standard protocol supported by modern instruments

### Device Discovery

USB TMC devices appear as `/dev/usbtmc*` on Linux. BenchMesh provides automatic discovery:

```bash
# List available USB TMC devices
curl http://localhost:57666/usbtmc-devices

# Response includes device metadata:
[
  {
    "device": "/dev/usbtmc0",
    "name": "usbtmc0",
    "vendor_id": "0x5345",
    "product_id": "0x1234",
    "manufacturer": "OWON",
    "product": "DGE2070"
  }
]
```

### Linux udev Rules

For persistent device paths (recommended), create udev rules based on USB vendor/product IDs:

```bash
# /etc/udev/rules.d/99-usbtmc-benchmesh.rules
SUBSYSTEM=="usbmisc", ATTRS{idVendor}=="5345", ATTRS{idProduct}=="1234", SYMLINK+="tmcDGE2070"
```

After creating the rule:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then reference the persistent path in config.yaml:
```yaml
device: /dev/tmcDGE2070  # Persistent symlink
```

### Driver Manifest Transport Support

Drivers declare which transports they support in `manifest.json`:

```json
{
  "vendor": "OWON",
  "family": "DGE",
  "supported_transports": ["serial", "usbtmc"],
  "models": { ... }
}
```

The system validates that the configured transport is supported by the driver at connection time.

### Enabling USB TMC Drivers

Some USB TMC drivers may be disabled by default in their manifest (e.g., owon_dge):

```json
{
  "enabled": false,  // Change to true to enable
  "supported_transports": ["serial", "usbtmc"],
  ...
}
```

Set `"enabled": true` to make the driver available in the Configuration UI.
