# Troubleshooting & FAQ

Common issues and solutions for BenchMesh.

## Table of Contents

- [Connection Issues](#connection-issues)
- [Device Communication](#device-communication)
- [UI Problems](#ui-problems)
- [API Issues](#api-issues)
- [Performance](#performance)
- [Installation Problems](#installation-problems)
- [FAQ](#faq)

## Connection Issues

### Device Won't Connect

**Symptom**: Device shows as "disconnected" in dashboard

**Solutions**:

1. **Check serial port permissions** (Linux):
   ```bash
   # Check current permissions
   ls -l /dev/ttyUSB0

   # Add user to dialout group
   sudo usermod -a -G dialout $USER

   # Log out and back in for changes to take effect
   newgrp dialout

   # Verify group membership
   groups
   ```

2. **Verify port path**:
   ```bash
   # Linux - List USB serial devices
   ls -l /dev/ttyUSB*
   ls -l /dev/ttyACM*

   # Show device info
   dmesg | grep tty

   # Use udevadm for detailed info
   udevadm info --name=/dev/ttyUSB0 --attribute-walk
   ```

   ```cmd
   REM Windows - Check Device Manager
   devmgmt.msc
   REM Look under "Ports (COM & LPT)"
   ```

3. **Check if port is already in use**:
   ```bash
   # Linux
   lsof | grep ttyUSB0

   # Kill process using port
   sudo pkill -9 -f ttyUSB0
   ```

4. **Verify device is powered on** and cable is properly connected

5. **Check baud rate** matches device specifications:
   ```yaml
   # config.yaml
   devices:
     - id: my-device
       baud: 9600  # Must match device settings
   ```

### Permission Denied Errors

**Error**: `PermissionError: [Errno 13] Permission denied: '/dev/ttyUSB0'`

**Solutions**:

1. **Add user to dialout group** (most common):
   ```bash
   sudo usermod -a -G dialout $USER
   logout  # Or reboot
   ```

2. **Temporary permission (not recommended)**:
   ```bash
   sudo chmod 666 /dev/ttyUSB0
   ```

3. **Create udev rule** for persistent permissions:
   ```bash
   # Create rule file
   sudo nano /etc/udev/rules.d/99-benchmesh.rules

   # Add rule (replace with your vendor/product ID)
   SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666", GROUP="dialout"

   # Reload rules
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

   Find vendor/product ID:
   ```bash
   lsusb
   # Output: Bus 001 Device 004: ID 1a86:7523 QinHeng Electronics CH340
   ```

### Device Keeps Disconnecting

**Symptom**: Device connects then disconnects repeatedly

**Solutions**:

1. **Check cable quality** - Use high-quality USB cables
2. **Check power supply** - Device may be underpowered
3. **Disable USB autosuspend** (Linux):
   ```bash
   # Temporarily disable
   echo -1 | sudo tee /sys/module/usbcore/parameters/autosuspend

   # Or disable for specific device
   echo 'on' | sudo tee /sys/bus/usb/devices/1-1/power/control
   ```

4. **Check logs** for error patterns:
   ```bash
   # Watch logs in real-time
   tail -f logs/benchmesh_service.log

   # Search for errors
   grep ERROR logs/benchmesh_service.log
   ```

5. **Increase reconnect timeout** in code (if needed)

### Multiple Devices on Same Port

**Error**: `SerialException: [Errno 16] Resource busy`

**Solutions**:

1. **Check for other processes**:
   ```bash
   lsof | grep ttyUSB0
   ```

2. **Stop conflicting services**:
   ```bash
   sudo systemctl stop modemmanager  # Often interferes with serial devices
   ```

3. **Verify config.yaml** doesn't have duplicate port entries

## Device Communication

### Device Not Responding

**Symptom**: Commands sent but no response received

**Solutions**:

1. **Verify EOL characters** in manifest:
   ```json
   {
     "connection": {
       "seol": "\r\n",  // Send EOL
       "reol": "\r\n"   // Receive EOL
     }
   }
   ```

   Common EOL combinations:
   - `\r\n` (CRLF) - Most common
   - `\n` (LF) - Unix style
   - `\r` (CR) - Mac style
   - `""` (empty) - No EOL

2. **Test with driver CLI**:
   ```bash
   PYTHONPATH=benchmesh-serial-service/src \
   python -m benchmesh_service.tools.driver_cli call \
       --id device-1 \
       --method query_identify \
       --config config.yaml
   ```

3. **Check timeout settings** - Some devices are slow to respond

4. **Verify command syntax** matches device manual

5. **Enable debug logging**:
   ```bash
   PYTHONPATH=benchmesh-serial-service/src \
   BENCHMESH_LOG_LEVEL=DEBUG \
   python -m benchmesh_service.main --config config.yaml
   ```

### Garbled or Incorrect Responses

**Solutions**:

1. **Verify baud rate** matches device:
   ```yaml
   baud: 9600  # Common rates: 9600, 19200, 38400, 57600, 115200
   ```

2. **Check serial format** (data bits, parity, stop bits):
   ```yaml
   serial: 8N1  # 8 data bits, No parity, 1 stop bit
   # Other formats: 7E1, 7O1, 8E1, 8N2, etc.
   ```

3. **Test with serial terminal**:
   ```bash
   # Install minicom
   sudo apt-get install minicom

   # Open port
   minicom -D /dev/ttyUSB0 -b 9600

   # Type commands manually to verify device works
   *IDN?
   ```

4. **Check for flow control** - Some devices need RTS/CTS

### IDN Not Matching

**Symptom**: Device connects but shows wrong identification

**Solutions**:

1. **Check ID patterns** in manifest:
   ```json
   {
     "models": {
       "MY-MODEL": {
         "id_patterns": [
           "ACME PowerPro 3000"  // Must match actual *IDN? response
         ]
       }
     }
   }
   ```

2. **Verify *IDN? command** is correct for your device:
   ```python
   # Some devices use different commands
   def query_identify(self):
       self.t.write_line('ID?')  # Not *IDN?
       return self.t.read_until_reol(1024)
   ```

3. **Check model override** in config:
   ```yaml
   devices:
     - id: device-1
       model: MY-MODEL  # Force specific model
   ```

## UI Problems

### UI Not Loading

**Solutions**:

1. **Check backend is running**:
   ```bash
   curl http://localhost:57666/status
   ```

2. **Verify port is correct** - Default is 57666

3. **Check firewall**:
   ```bash
   # Linux - Allow port
   sudo ufw allow 57666

   # Check if port is listening
   ss -tulpn | grep 57666
   ```

4. **Clear browser cache** and reload

5. **Check browser console** for errors (F12)

### WebSocket Not Connecting

**Error**: "WebSocket connection failed"

**Solutions**:

1. **Verify WebSocket endpoint** is accessible:
   ```javascript
   // Should be ws://localhost:57666/ws
   ```

2. **Check for proxy issues** - Some proxies block WebSockets

3. **Verify backend logs** for connection errors

4. **Test with websocat**:
   ```bash
   # Install websocat
   cargo install websocat

   # Test connection
   websocat ws://localhost:57666/ws
   ```

### UI Not Updating

**Symptom**: Device status not refreshing in real-time

**Solutions**:

1. **Check WebSocket connection** in browser dev tools

2. **Verify polling is running** in backend logs

3. **Refresh browser** (Ctrl+F5 for hard refresh)

4. **Check device is connected** and responding

## API Issues

### 404 Not Found

**Error**: `GET /instruments/PSU/device-1/voltage` returns 404

**Solutions**:

1. **Verify device ID** matches config:
   ```bash
   curl http://localhost:57666/instruments
   ```

2. **Check device class** is correct (PSU, DMM, etc.)

3. **Verify method exists** on driver:
   ```bash
   python -m benchmesh_service.tools.driver_cli methods \
       --id device-1 --config config.yaml
   ```

4. **Check URL format**:
   ```
   GET  /instruments/{class}/{id}/{channel}/{method}
   POST /instruments/{class}/{id}/{channel}/{method}/{value}
   ```

### Method Not Found

**Error**: `Method 'voltage' not found on driver`

**Solutions**:

1. **Use correct method prefix**:
   - GET requests need `query_` methods
   - POST requests need `set_` methods

   ```python
   # GOOD
   def query_voltage(self, channel: int):
       pass

   # BAD
   def get_voltage(self, channel: int):  # Wrong prefix
       pass
   ```

2. **Check API documentation**:
   ```bash
   open http://localhost:57666/docs
   ```

### Authentication Errors

BenchMesh currently has no authentication. If you need security:

1. **Use reverse proxy** with auth:
   ```nginx
   # nginx.conf
   location / {
       proxy_pass http://localhost:57666;
       auth_basic "BenchMesh";
       auth_basic_user_file /etc/nginx/.htpasswd;
   }
   ```

2. **Use SSH tunnel** for remote access:
   ```bash
   ssh -L 57666:localhost:57666 user@remote-host
   ```

## Performance

### Slow Response Times

**Solutions**:

1. **Reduce polling frequency** in manifest:
   ```json
   {
     "polling": {
       "interval": 5.0  // Increase from 2.0 to 5.0 seconds
     }
   }
   ```

2. **Disable unnecessary polling**:
   ```json
   {
     "polling": {
       "methods": []  // Disable automatic polling
     }
   }
   ```

3. **Check device response times** - Some devices are slow

4. **Use faster serial port** if supported (higher baud rate)

### High CPU Usage

**Solutions**:

1. **Check for polling loops** in logs

2. **Reduce polling frequency** (see above)

3. **Check for stuck threads**:
   ```bash
   # Get thread dump
   kill -SIGUSR1 <pid>
   ```

4. **Profile with cProfile**:
   ```bash
   python -m cProfile -o profile.stats \
       benchmesh-serial-service/src/benchmesh_service/main.py
   ```

### Memory Leaks

**Solutions**:

1. **Restart service periodically** (temporary fix)

2. **Check for unclosed connections**

3. **Profile memory usage**:
   ```python
   import tracemalloc
   tracemalloc.start()
   # ... run service ...
   snapshot = tracemalloc.take_snapshot()
   top_stats = snapshot.statistics('lineno')
   for stat in top_stats[:10]:
       print(stat)
   ```

## Installation Problems

### pip Install Fails

**Error**: `ERROR: Could not find a version that satisfies the requirement...`

**Solutions**:

1. **Update pip**:
   ```bash
   pip install --upgrade pip
   ```

2. **Use Python 3.8+**:
   ```bash
   python3 --version
   ```

3. **Install from requirements.txt**:
   ```bash
   pip install -r benchmesh-serial-service/requirements.txt
   ```

4. **Check Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

### npm Install Fails

**Solutions**:

1. **Use Node.js 16+**:
   ```bash
   node --version
   ```

2. **Clear npm cache**:
   ```bash
   npm cache clean --force
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Use npm ci** instead of npm install:
   ```bash
   npm ci
   ```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'benchmesh_service'`

**Solutions**:

1. **Set PYTHONPATH**:
   ```bash
   export PYTHONPATH=benchmesh-serial-service/src
   ```

2. **Install in editable mode**:
   ```bash
   pip install -e benchmesh-serial-service
   ```

3. **Run from correct directory**:
   ```bash
   cd /path/to/BenchMesh
   ./start.sh
   ```

## FAQ

### General

**Q: What devices are supported?**

A: BenchMesh supports any serial device with a driver. Included drivers:
- TENMA 72-series Power Supplies
- OWON SPM3000 Series Power Meters
- OWON XDM Series Multimeters
- OWON OEL Series Electronic Loads
- OWON DGE Series Function Generators

New drivers can be added - see [Driver Development](Driver-Development).

**Q: Can I use BenchMesh remotely?**

A: Yes, but use SSH tunneling or VPN for security:
```bash
ssh -L 57666:localhost:57666 user@lab-server
# Access via http://localhost:57666
```

**Q: Does BenchMesh work on Windows?**

A: Yes. Change port names to `COM3`, `COM4`, etc. in config.yaml.

**Q: Can I control multiple devices simultaneously?**

A: Yes. Add all devices to config.yaml. Each runs in its own thread.

**Q: Does BenchMesh save measurements?**

A: No. BenchMesh is for control and monitoring. Use Node-RED for data logging:
```javascript
// Node-RED function node
msg.payload = {
    timestamp: Date.now(),
    voltage: msg.payload.voltage,
    current: msg.payload.current
};
return msg;
```

### Configuration

**Q: How do I find my serial port?**

```bash
# Linux
ls -l /dev/ttyUSB* /dev/ttyACM*
dmesg | grep tty

# Mac
ls -l /dev/cu.*

# Windows
# Check Device Manager > Ports (COM & LPT)
```

**Q: What baud rate should I use?**

A: Check your device manual. Common rates: 9600, 19200, 38400, 57600, 115200.

**Q: Do I need to restart after changing config?**

A: Yes. Changes to config.yaml require backend restart.

**Q: Can I have multiple devices on one physical port?**

A: No. Each device needs its own serial port.

### Development

**Q: How do I add a new device driver?**

A: See [Driver Development Guide](Driver-Development).

**Q: Can I use BenchMesh as a library?**

A: Yes:
```python
from benchmesh_service.serial_manager import SerialManager

config = {...}  # Load config
manager = SerialManager(config)
manager.start()

# Use devices
status = manager.get_device_status('device-1')
```

**Q: How do I contribute?**

A: See [Contributing Guide](../CONTRIBUTING.md). We welcome:
- New device drivers
- Bug fixes
- Documentation improvements
- Feature requests

**Q: Can I use BenchMesh commercially?**

A: Yes. BenchMesh is MIT licensed. See [LICENSE](../LICENSE).

### Automation

**Q: How do I automate measurements?**

A: Use Node-RED for automation. See [Automation Guide](Automation).

**Q: Can I call the API from Python/JavaScript?**

A: Yes:
```python
import requests

# Get device status
r = requests.get('http://localhost:57666/instruments')
devices = r.json()

# Set voltage
r = requests.post('http://localhost:57666/instruments/PSU/psu-1/1/voltage/12.0')
```

```javascript
// Get device status
const response = await fetch('http://localhost:57666/instruments');
const devices = await response.json();

// Set voltage
await fetch('http://localhost:57666/instruments/PSU/psu-1/1/voltage/12.0', {
  method: 'POST'
});
```

**Q: Can I schedule automated tests?**

A: Yes, use cron with Node-RED flows or direct API calls:
```bash
# crontab -e
0 * * * * curl -X POST http://localhost:57666/instruments/PSU/psu-1/1/output/true
```

### Troubleshooting

**Q: Where are the logs?**

A: Logs are in `logs/benchmesh_service.log` (if logging is configured).

**Q: How do I enable debug logging?**

```bash
BENCHMESH_LOG_LEVEL=DEBUG ./start.sh
```

**Q: Device works with minicom but not BenchMesh?**

A: Check EOL characters and baud rate in manifest match minicom settings.

**Q: How do I report a bug?**

A: Open an issue at [GitHub Issues](https://github.com/MarkoVcode/BenchMesh/issues) with:
- BenchMesh version
- Operating system
- Device model
- Config file (sanitized)
- Error logs
- Steps to reproduce

## Getting Help

- **Documentation**: [BenchMesh Wiki](Home)
- **Issues**: [GitHub Issues](https://github.com/MarkoVcode/BenchMesh/issues)
- **Discussions**: [GitHub Discussions](https://github.com/MarkoVcode/BenchMesh/discussions)

## Related Documentation

- [Getting Started](Getting-Started) - Installation and setup
- [Configuration](Configuration) - Config file format
- [Driver Development](Driver-Development) - Creating drivers
- [API Reference](API-Reference) - API documentation
