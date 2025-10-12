# Configuration

BenchMesh uses a YAML configuration file to define connected devices and their settings.

## Configuration File Location

The configuration file is located at:
```
benchmesh-serial-service/config.yaml
```

## Configuration Format

The configuration uses YAML v1 schema:

```yaml
version: 1
devices:
  - id: tenmapsu-1              # Unique device ID
    name: "TENMA PSU"            # Display name
    driver: tenma_psu            # Driver name
    port: /dev/tty722540         # Serial port path
    baud: 9600                   # Baud rate
    serial: 8N1                  # Data bits, parity, stop bits
    model: 72-2540               # Optional model override
```

## Configuration Fields

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `id` | Unique identifier for the device | `psu-1`, `dmm-bench` |
| `name` | Human-readable display name | `"Bench Power Supply"` |
| `driver` | Driver module name | `tenma_72`, `owon_xdm` |
| `port` | Serial port path | `/dev/ttyUSB0`, `COM3` |
| `baud` | Baud rate | `9600`, `115200` |
| `serial` | Serial format (data-parity-stop) | `8N1`, `7E1` |

### Optional Fields

| Field | Description | Example |
|-------|-------------|---------|
| `model` | Override device model detection | `72-2540` |

## Serial Port Formats

The `serial` field specifies data bits, parity, and stop bits:

- **Data bits**: `7` or `8`
- **Parity**: `N` (none), `E` (even), `O` (odd)
- **Stop bits**: `1` or `2`

Common formats:
- `8N1` - 8 data bits, no parity, 1 stop bit (most common)
- `7E1` - 7 data bits, even parity, 1 stop bit
- `8E1` - 8 data bits, even parity, 1 stop bit

## Available Drivers

BenchMesh includes drivers for various instruments:

### Power Supplies (PSU)
- `tenma_72` (alias: `tenma_psu`) - Tenma 72-series programmable power supplies

### Spectrum Analyzers (SAL)
- `owon_xsa` - OWON XSA series spectrum analyzers

### Digital Multimeters (DMM)
- `owon_xdm` - OWON XDM series multimeters

### Electronic Loads (ELL)
- `owon_oel` - OWON OEL series electronic loads

### Function Generators (AWG)
- `owon_dge` - OWON DGE series function generators

## Serial Port Discovery

### Linux

List available serial ports:
```bash
ls -l /dev/ttyUSB*
ls -l /dev/ttyACM*
```

For persistent device paths, use udev rules:
```bash
# Find device serial number
udevadm info -a -n /dev/ttyUSB0 | grep serial

# Create rule in /etc/udev/rules.d/99-benchmesh.rules
SUBSYSTEM=="tty", ATTRS{serial}=="A50285BI", SYMLINK+="tty722540"
```

### Windows

Serial ports appear as `COM1`, `COM2`, etc.

Check Device Manager:
1. Open Device Manager
2. Expand "Ports (COM & LPT)"
3. Note the COM port number

### macOS

List available ports:
```bash
ls -l /dev/tty.usb*
ls -l /dev/cu.usb*
```

## Configuration Best Practices

1. **Use descriptive IDs**: Makes automation scripts more readable
2. **Persistent port paths**: Use udev rules on Linux for stable device paths
3. **Document custom models**: If using model overrides, document why
4. **Backup configuration**: Keep a backup copy of `config.yaml`

## Modifying Configuration

### Via UI (Recommended)

1. Click **⚙️ Configuration** in the top bar
2. Add, edit, or remove devices
3. Click **Save Configuration**
4. Restart the service for changes to take effect

### Manual Editing

1. Stop the BenchMesh service
2. Edit `benchmesh-serial-service/config.yaml`
3. Validate YAML syntax
4. Restart the service

## Configuration Validation

The system validates configuration on startup:

- **Required fields**: Checks all required fields are present
- **Driver existence**: Verifies driver module exists
- **Unique IDs**: Ensures all device IDs are unique
- **Serial format**: Validates serial format string

Validation errors appear in the console log on startup.

## Example Configurations

### Single Power Supply

```yaml
version: 1
devices:
  - id: psu-1
    name: "Bench PSU"
    driver: tenma_72
    port: /dev/ttyUSB0
    baud: 9600
    serial: 8N1
```

### Multiple Instruments

```yaml
version: 1
devices:
  - id: psu-main
    name: "Main Power Supply"
    driver: tenma_72
    port: /dev/ttyUSB0
    baud: 9600
    serial: 8N1

  - id: dmm-bench
    name: "Bench Multimeter"
    driver: owon_xdm
    port: /dev/ttyUSB1
    baud: 115200
    serial: 8N1

  - id: load-1
    name: "Electronic Load"
    driver: owon_oel
    port: /dev/ttyUSB2
    baud: 115200
    serial: 8N1
```

## Environment Variables

Override default configuration path:

```bash
export BENCHMESH_CONFIG=/path/to/custom/config.yaml
python -m benchmesh_service.main
```
