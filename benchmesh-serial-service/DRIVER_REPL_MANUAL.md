# Driver REPL Manual

Interactive driver testing console with persistent state for BenchMesh serial drivers.

## Overview

`driver_repl.py` is an interactive REPL (Read-Eval-Print Loop) tool for testing driver methods while maintaining persistent driver state, transport connection, and cache across multiple commands.

Unlike `driver_cli.py` which creates a new driver instance for each command (losing cache state), the REPL maintains a single driver instance throughout the session, providing a more realistic testing environment for cache-dependent behavior.

## Key Features

### Persistence
- **Single driver instance** - Created once on startup, reused for all commands
- **Persistent transport** - Connection stays open throughout session
- **Cache state maintained** - Cache persists across method calls for realistic testing
- **Realistic behavior** - Tests drivers exactly as they behave in production

### Interactive Console
- **Command history** - Navigate previous commands with arrow keys
- **Tab completion** - (inherited from Python cmd module)
- **Help system** - Built-in help for all commands
- **Error handling** - Clear error messages for troubleshooting

### Cache Management
- **Inspect cache** - View cache statistics and contents
- **Clear cache** - Reset all cached values
- **Invalidate keys** - Remove specific cache entries
- **Monitor hits/misses** - Track cache performance

### Method Testing
- **Automatic type conversion** - Arguments converted to correct types (int, float, bool, str)
- **Method discovery** - List all available driver methods with signatures
- **Filtering** - Find methods by name pattern (e.g., "query", "set")
- **Return value display** - Pretty-print JSON objects and strings

## Installation

No installation required. The tool is part of the benchmesh-serial-service package.

### Prerequisites

- Python 3.8+
- BenchMesh serial service installed
- Valid `config.yaml` with device configurations

## Usage

### Starting the REPL

```bash
# From repository root
cd benchmesh-serial-service

# Start REPL for a specific device
PYTHONPATH=src python3 -m benchmesh_service.tools.driver_repl \
  --id <device-id> \
  --config <config-file>
```

### Quick Start Example

```bash
# Start REPL for DMM device
PYTHONPATH=src python3 -m benchmesh_service.tools.driver_repl \
  --id dmm-1 \
  --config config.yaml
```

### Command Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--id` | Yes | - | Device ID from config file |
| `--config` | No | `config.yaml` | Path to configuration file |

## Available Commands

### Device Control

#### `call <method> [args...]`
Call a driver method with optional arguments.

**Examples:**
```
(dmm-1) call query_identify
OWON,XDM1241,SN:123456,V1.0.0

(dmm-1) call set_mode 1 RES
(no return value)

(dmm-1) call query_voltage 1
12.345

(dmm-1) call set_output true
(no return value)
```

**Argument Type Conversion:**
- `int` parameters: `"123"` → `123`
- `float` parameters: `"3.14"` → `3.14`
- `bool` parameters: `"true"`, `"1"`, `"yes"`, `"on"` → `True`
- `str` parameters: Used as-is

#### `methods [filter]`
List all available driver methods with signatures.

**Examples:**
```
(dmm-1) methods
Available methods on OwonXdmDriver:
------------------------------------------------------------
  close()
  is_connected() -> bool
  poll_status(channel: int) -> dict
  query_current(channel: int) -> str
  query_identify() -> str
  query_mode(channel: int) -> str
  query_voltage(channel: int) -> str
  set_mode(channel: int, mode: str)
  set_range(channel: int, range_value: str)

(dmm-1) methods query
Available methods on OwonXdmDriver:
------------------------------------------------------------
  query_current(channel: int) -> str
  query_identify() -> str
  query_mode(channel: int) -> str
  query_voltage(channel: int) -> str

(dmm-1) methods set
Available methods on OwonXdmDriver:
------------------------------------------------------------
  set_mode(channel: int, mode: str)
  set_range(channel: int, range_value: str)
```

### Cache Management

#### `cache_stats`
Display cache statistics and contents.

**Example:**
```
(dmm-1) cache_stats

Cache Statistics:
------------------------------------------------------------
  Total entries: 3
  Hits: 5
  Misses: 3
  Hit rate: 62.5%
  Evictions: 0

Cache contents:
  mode_1: RES (expires in 1.8s)
  voltage_1: 12.345 (expires in 0.3s)
  current_1: 0.0012 (expires in 1.2s)
```

#### `cache_clear`
Clear all cached values.

**Example:**
```
(dmm-1) cache_clear
Cache cleared
```

#### `cache_invalidate <key>`
Invalidate a specific cache key.

**Example:**
```
(dmm-1) cache_invalidate mode_1
Invalidated cache key: mode_1
```

### Device Information

#### `info`
Display device and connection information.

**Example:**
```
(dmm-1) info

Device Information:
------------------------------------------------------------
  Device ID: dmm-1
  Driver: owon_xdm
  Transport: serial
  Port: /dev/ttyXDM1241
  Baud: 115200
  Driver class: OwonXdmDriver
  Connected: Yes
```

#### `reconnect`
Close the existing connection and reconnect to the device.

**Use this when:**
- Device was disconnected and reconnected
- Testing connection recovery behavior
- Clearing cache and re-initializing driver

**Example:**
```
(dmm-1) reconnect
Reconnecting...
Connected to dmm-1: OWON,XDM1241,SN:123456,V1.0.0
Reconnected successfully
```

### Session Control

#### `exit` / `quit` / `Ctrl+D`
Exit the REPL.

**Example:**
```
(dmm-1) exit
Closing connection and exiting...
```

#### `help [command]`
Display help information.

**Examples:**
```
(dmm-1) help
Documented commands (type help <topic>):
========================================
EOF          cache_invalidate  call  help  methods  reconnect
cache_clear  cache_stats       exit  info  quit

(dmm-1) help call
Call a driver method with arguments.

Usage: call <method_name> [args...]

Examples:
    call query_voltage 1
    call set_mode 1 RES
    call query_identify
```

## Workflow Examples

### Example 1: Testing Cache Behavior

```bash
# Start REPL
PYTHONPATH=src python3 -m benchmesh_service.tools.driver_repl --id dmm-1 --config config.yaml

# Test cache behavior
(dmm-1) cache_stats                # Initial state
(dmm-1) call query_mode 1          # Cache miss
RES
(dmm-1) cache_stats                # Should show 1 entry, 1 miss
(dmm-1) call query_mode 1          # Cache hit!
RES
(dmm-1) cache_stats                # Should show 1 hit
(dmm-1) call set_mode 1 VOLT       # Invalidates cache
(dmm-1) cache_stats                # Entry should be gone
(dmm-1) call query_mode 1          # Cache miss again
VOLT
(dmm-1) exit
```

### Example 2: Method Discovery

```bash
# Start REPL
PYTHONPATH=src python3 -m benchmesh_service.tools.driver_repl --id psu-1 --config config.yaml

# Discover available methods
(psu-1) methods                    # All methods
(psu-1) methods query              # Only query methods
(psu-1) methods set                # Only set methods
(psu-1) methods voltage            # Methods with "voltage" in name
(psu-1) exit
```

### Example 3: Testing Device Commands

```bash
# Start REPL
PYTHONPATH=src python3 -m benchmesh_service.tools.driver_repl --id psu-1 --config config.yaml

# Test PSU commands
(psu-1) info                       # Check connection
(psu-1) call query_identify        # Get device ID
(psu-1) call set_voltage 1 5.0     # Set voltage to 5V
(psu-1) call query_voltage 1       # Read back voltage
5.000
(psu-1) call set_current 1 1.0     # Set current limit
(psu-1) call set_output 1 true     # Enable output
(psu-1) call query_status 1        # Check status
{"voltage": "5.000", "current": "0.123", "output": true}
(psu-1) call set_output 1 false    # Disable output
(psu-1) exit
```

### Example 4: Debugging Connection Issues

```bash
# Start REPL
PYTHONPATH=src python3 -m benchmesh_service.tools.driver_repl --id dmm-1 --config config.yaml

# If device fails to connect
ERROR: Failed to connect: [Errno 2] No such file or directory: '/dev/ttyXDM1241'

# Check device info even when disconnected
(dmm-1) info
Device Information:
------------------------------------------------------------
  Device ID: dmm-1
  Driver: owon_xdm
  Transport: serial
  Port: /dev/ttyXDM1241
  Baud: 115200
  Connected: No

# Fix the issue (reconnect USB, etc.), then reconnect
(dmm-1) reconnect
Reconnecting...
Connected to dmm-1: OWON,XDM1241,SN:123456,V1.0.0
Reconnected successfully

# Now try commands
(dmm-1) call query_voltage 1
12.345
```

## Comparison with driver_cli

### driver_cli (Old Tool)

**Usage:**
```bash
# Each command creates new driver instance
python -m benchmesh_service.tools.driver_cli call --id dmm-1 --method query_mode 1 --config config.yaml
python -m benchmesh_service.tools.driver_cli call --id dmm-1 --method set_mode 1 RES --config config.yaml
python -m benchmesh_service.tools.driver_cli call --id dmm-1 --method query_mode 1 --config config.yaml
```

**Limitations:**
- ❌ Creates new SerialManager for each command
- ❌ Creates new driver instance for each command
- ❌ Opens/closes transport for each command
- ❌ **Cache is lost between commands**
- ❌ Cannot observe cache behavior
- ❌ Slow (connection overhead per command)
- ❌ Not interactive

### driver_repl (New Tool)

**Usage:**
```bash
# One session, persistent driver
python -m benchmesh_service.tools.driver_repl --id dmm-1 --config config.yaml
(dmm-1) call query_mode 1
(dmm-1) call set_mode 1 RES
(dmm-1) call query_mode 1
(dmm-1) cache_stats
(dmm-1) exit
```

**Benefits:**
- ✅ Single driver instance throughout session
- ✅ Persistent transport connection
- ✅ **Cache persists across commands**
- ✅ Can observe and manage cache
- ✅ Fast (no connection overhead)
- ✅ Interactive with history

**When to Use Each:**

| Scenario | Tool |
|----------|------|
| One-off command in script | `driver_cli` |
| Testing cache behavior | `driver_repl` |
| Interactive exploration | `driver_repl` |
| Debugging driver methods | `driver_repl` |
| CI/CD automated tests | `driver_cli` |
| Manual device testing | `driver_repl` |

## Implementation Details

### Driver Creation

The REPL follows the same driver creation pattern as SerialManager:

1. Load driver class using `DriverFactory.load_driver_class()`
2. Get EOL settings from manifest using `ManifestResolver.get_connection_eol()`
3. Create transport (Serial, USB TMC, etc.)
4. Open transport connection
5. Instantiate driver with transport
6. Cache is automatically attached by `DriverBase`

### Cache Integration

All drivers inherit from `DriverBase`, which automatically creates a `SimpleCache` instance:

```python
# In DriverBase.__init__
self.cache = SimpleCache()
```

The REPL accesses this cache instance for statistics and management:

```python
# Cache statistics
stats = self.driver.cache.get_stats()

# Clear cache
self.driver.cache.clear()

# Invalidate key
self.driver.cache.invalidate(key)
```

### Method Invocation

The `call` command uses Python introspection to:

1. Find the method on the driver
2. Extract parameter signatures
3. Convert string arguments to correct types
4. Call the method with converted arguments
5. Pretty-print the return value

```python
# Example: call set_voltage 1 5.0
method = getattr(driver, 'set_voltage')
sig = inspect.signature(method)
# Convert: "1" -> 1 (int), "5.0" -> 5.0 (float)
result = method(1, 5.0)
```

## Troubleshooting

### Device Not Found

**Error:**
```
ERROR: Device 'xyz-1' not found in config
```

**Solution:**
Check available devices:
```bash
PYTHONPATH=src python3 -m benchmesh_service.tools.driver_cli list --config config.yaml
```

### Connection Failed

**Error:**
```
ERROR: Failed to connect: [Errno 2] No such file or directory: '/dev/ttyXDM1241'
```

**Possible Causes:**
1. Device not connected
2. Wrong port path
3. USB device not enumerated
4. Permission issues

**Solutions:**
```bash
# Check device is connected
ls -l /dev/tty*

# Check udev rules are loaded
cat /etc/udev/rules.d/99-benchmesh.rules

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Check permissions
sudo usermod -a -G dialout $USER
# Logout and login again
```

### Method Not Found

**Error:**
```
ERROR: Method 'query_xyz' not found on driver
Use 'methods' to see available methods
```

**Solution:**
List available methods:
```
(device-1) methods
```

### Type Conversion Error

**Error:**
```
ERROR: Cannot convert argument 1 to int: invalid literal for int() with base 10: 'abc'
```

**Solution:**
Check method signature and provide correct argument types:
```
(device-1) methods                  # Check signature
(device-1) call set_mode 1 RES      # Use correct types
```

### Cache Not Available

**Error:**
```
Driver does not have a SimpleCache instance
```

**Cause:**
Driver doesn't inherit from `DriverBase` or overrides `__init__` without calling `super().__init__()`.

**Solution:**
Check driver implementation and ensure it inherits from `DriverBase`.

## Advanced Usage

### Testing Cache TTL

```bash
(dmm-1) cache_stats                    # Check initial state
(dmm-1) call query_mode 1              # Cache miss, sets entry
(dmm-1) cache_stats                    # See TTL countdown
# Wait for TTL to expire...
(dmm-1) cache_stats                    # Entry should be gone
(dmm-1) call query_mode 1              # Cache miss again
```

### Testing Cache Invalidation

```bash
(dmm-1) call query_voltage 1           # Populate cache
(dmm-1) cache_stats                    # Verify entry exists
(dmm-1) call set_voltage 1 5.0         # Should invalidate cache
(dmm-1) cache_stats                    # Entry should be gone
```

### Method Signature Inspection

```bash
(dmm-1) methods
# Output shows signatures:
#   set_mode(channel: int, mode: str)
#   query_voltage(channel: int) -> str
```

Use this to understand required parameter types and return values.

## Tips and Best Practices

### 1. Use Tab Completion
The cmd module provides basic tab completion for commands.

### 2. Check Cache Stats Frequently
Monitor cache behavior to understand driver performance:
```
(dmm-1) cache_stats
```

### 3. Use Method Filtering
Quickly find methods by prefix:
```
(dmm-1) methods query    # All query methods
(dmm-1) methods set      # All set methods
```

### 4. Test Reconnection
Verify driver handles reconnection correctly:
```
(dmm-1) reconnect
```

### 5. Check Device Info First
Always verify connection before testing:
```
(dmm-1) info
```

### 6. Use History
Navigate previous commands with ↑/↓ arrow keys.

### 7. Ctrl+D to Exit
Quick exit without typing "exit".

## Future Enhancements

Potential improvements for future versions:

- [ ] Tab completion for method names
- [ ] Tab completion for cache keys
- [ ] Command aliases (e.g., `c` for `call`)
- [ ] Multi-line command support
- [ ] Command scripts/playback
- [ ] History persistence across sessions
- [ ] Output redirection to file
- [ ] Batch mode (read commands from file)
- [ ] Performance timing for method calls
- [ ] Mock mode (no actual device connection)

## See Also

- `driver_cli.py` - One-shot driver command execution
- `CACHE_DESIGN.md` - SimpleCache implementation details
- `TESTING_GUIDE.md` - Comprehensive testing documentation
- `benchmesh-serial-service/src/benchmesh_service/drivers/base.py` - DriverBase implementation

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/your-org/benchmesh/issues
- Documentation: `ai_context/` directory
- Driver Examples: `benchmesh-serial-service/src/benchmesh_service/drivers/`
