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

## Documentation

### Getting Started

- **[Getting Started](Getting-Started)** - Installation, first-time setup, and quick start guide
- **[Configuration](Configuration)** - Device configuration, YAML format, and manifest system
- **[Troubleshooting](Troubleshooting)** - Common issues, solutions, and FAQ

### Using BenchMesh

- **[API Reference](API-Reference)** - Complete REST API documentation with examples
- **[Automation](Automation)** - Node-RED integration and workflow automation

### Development

- **[Architecture](Architecture)** - System design, components, and design decisions
- **[Driver Development](Driver-Development)** - Creating drivers for new devices
- **[Testing](Testing)** - Running tests, writing tests, and MCP service

### Production

- **[Deployment](Deployment)** - Production deployment with systemd, Docker, and reverse proxy

### Contributing

- **[Contributing Guide](https://github.com/MarkoVcode/BenchMesh/blob/main/CONTRIBUTING.md)** - How to contribute to BenchMesh

## Quick Start

1. **Install** - Follow the [Getting Started](Getting-Started) guide
2. **Configure** - Add your devices in [Configuration](Configuration)
3. **Control** - Use the dashboard or [API](API-Reference)
4. **Automate** - Create workflows with [Node-RED](Automation)

## System Architecture

BenchMesh consists of three main components:

1. **Backend Service** (`benchmesh-serial-service`) - Python FastAPI application managing serial device connections
2. **Frontend UI** - React-based web interface for device control and monitoring
3. **Node-RED Integration** - Visual programming environment for automation

All components run locally on your machine and communicate via HTTP/WebSocket on port 57666.

For detailed architecture information, see [Architecture](Architecture).

## Getting Help

- **Documentation**: Browse the pages above for detailed information
- **Troubleshooting**: Check [Troubleshooting](Troubleshooting) for common issues
- **Issues**: Report bugs at [GitHub Issues](https://github.com/MarkoVcode/BenchMesh/issues)
- **Discussions**: Ask questions at [GitHub Discussions](https://github.com/MarkoVcode/BenchMesh/discussions)

## License

BenchMesh is licensed under the **MIT License**. See the [LICENSE](https://github.com/MarkoVcode/BenchMesh/blob/main/LICENSE) file for details.
