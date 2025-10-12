# Getting Started

This guide will help you set up and start using BenchMesh.

## Prerequisites

- **Python 3.8+** - For the backend service
- **Node.js 16+** - For Node-RED (optional, for automation)
- **Serial Devices** - Lab instruments connected via USB-to-Serial or RS232

## Installation

### Starting the Complete System

The easiest way to start all components:

```bash
# From repository root
./start.sh
```

This starts:
- Backend API on port 57666
- Frontend UI (served by backend)
- Node-RED on port 1880

### Access Points

After starting, access:

- **Main UI**: http://localhost:57666
- **API Documentation**: http://localhost:57666/docs
- **Node-RED**: http://localhost:1880

## First-Time Setup

### 1. Configure Your First Device

1. Click **⚙️ Configuration** in the top bar
2. Click **Add Device**
3. Fill in device details:
   - **ID**: Unique identifier (e.g., `psu-1`)
   - **Name**: Display name (e.g., `Tenma PSU`)
   - **Driver**: Select from available drivers
   - **Port**: Serial port path (e.g., `/dev/ttyUSB0` or `COM3`)
   - **Baud Rate**: Device baud rate (e.g., `9600`)
   - **Serial Format**: Usually `8N1` (8 data bits, no parity, 1 stop bit)

4. Click **Save Configuration**

### 2. Verify Connection

After saving, the device should appear on the main dashboard with:
- **Green status indicator** if connected
- **Device identification** (from `*IDN?` command)
- **Real-time status** updates every 2 seconds

### 3. Control Your Device

Depending on the device class, you'll see:
- **PSU**: Voltage/current controls, output on/off
- **DMM**: Real-time measurements
- **AWG**: Waveform settings and controls

## Troubleshooting

### Device Won't Connect

1. **Check port permissions**:
   ```bash
   # Linux: Add user to dialout group
   sudo usermod -a -G dialout $USER
   # Log out and back in for changes to take effect
   ```

2. **Verify port path**:
   ```bash
   # Linux
   ls -l /dev/ttyUSB*

   # Windows
   # Check Device Manager > Ports (COM & LPT)
   ```

3. **Check baud rate**: Ensure it matches your device specifications

4. **View logs**: Check console output for connection errors

### Device Shows as Disconnected

- Device may be reconnecting (automatic retry every ~2s)
- Check physical cable connection
- Verify no other software is using the serial port
- Check device is powered on

### Configuration Changes Not Applying

- Configuration requires backend restart
- Stop the service and run `./start.sh` again

## Next Steps

- Learn about [Configuration](Configuration) options
- Set up [Automation](Automation) workflows with Node-RED
- Explore the [API Reference](API-Reference) for programmatic control
