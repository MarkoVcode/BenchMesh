# BenchMesh Documentation

Welcome to BenchMesh - a consistent, browser-based cockpit for lab instruments.

## What is BenchMesh?

BenchMesh connects, controls, logs, correlates, and automates multiple serial devices from a single browser interface. It provides a unified way to interact with various laboratory instruments including:

- **Power Supplies (PSU)** - Control voltage, current, and output state
- **Digital Multimeters (DMM)** - Read voltage, current, resistance, and temperature
- **Spectrum Analyzers (SAL)** - Frequency domain analysis
- **Oscilloscopes (OSC)** - Time domain waveform capture
- **Function Generators (AWG)** - Signal generation
- **Electronic Loads (ELL)** - Load testing
- **LCR Meters** - Inductance, capacitance, and resistance measurement

## Key Features

- **Browser-Based Interface** - No desktop software installation required
- **Multi-Device Support** - Connect and control multiple instruments simultaneously
- **Real-Time Updates** - Live data streaming via WebSocket
- **Automation Ready** - Node-RED integration for complex workflows
- **Offline Capable** - All documentation and UI shipped with the application
- **RESTful API** - Full programmatic control via HTTP endpoints

## Quick Start

1. Configure your devices in the **Configuration** panel
2. View real-time status and control instruments from the main dashboard
3. Use **Node-RED** for automation workflows
4. Access the **API Reference** for programmatic control

## System Architecture

BenchMesh consists of three main components:

1. **Backend Service** (`benchmesh-serial-service`) - Python FastAPI application managing serial device connections
2. **Frontend UI** - React-based web interface for device control and monitoring
3. **Node-RED Integration** - Visual programming environment for automation

All components run locally on your machine and communicate via HTTP/WebSocket on port 57666.

## Getting Help

- Check the chapters in the left sidebar for detailed information
- Visit the API Reference for programmatic control documentation
- Report issues at [GitHub Issues](https://github.com/anthropics/benchmesh/issues)
