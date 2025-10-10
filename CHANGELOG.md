# Changelog

All notable changes to BenchMesh will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.50] - 2025-10-10

### Added
-

### Changed
-

### Fixed
-

### Deprecated
-

### Removed
-

### Security
-


## [0.0.30] - 2025-10-10

### Added
-

### Changed
-

### Fixed
-

### Deprecated
-

### Removed
-

### Security
-


## [0.0.20] - 2025-10-09

### Added
-

### Changed
-

### Fixed
-

### Deprecated
-

### Removed
-

### Security
-


## [0.0.19] - 2025-10-09

### Added
-

### Changed
-

### Fixed
-

### Deprecated
-

### Removed
-

### Security
-


### Added
- Initial release preparation
- Electron desktop application wrapper
- GitHub Actions automated release workflow

## [0.1.0] - YYYY-MM-DD

### Added
- **Frontend UI**
  - React-based instrument control interface
  - Real-time WebSocket data streaming
  - Measurement recording and graphing
  - Time-series graph visualization with independent Y-axis scaling
  - CSV export functionality for measurements
  - Node-RED integration with browser access

- **Instrument Support**
  - Generic DMM (Digital Multimeter) component with mode selection
  - Generic PSU (Power Supply Unit) with voltage/current/power control
  - Generic ELL (Electronic Load) support
  - Generic AWG (Arbitrary Waveform Generator) placeholder
  - Generic OSC (Oscilloscope) placeholder
  - Generic LCR (LCR Meter) placeholder
  - Generic SAL (Spectrum Analyzer) placeholder
  - Dynamic range selection for DMM modes
  - Temperature mode support (placeholder)

- **Backend Services**
  - FastAPI-based REST API
  - WebSocket registry for real-time instrument data
  - Serial device management
  - Instrument driver system
  - Multi-channel support

- **Automation**
  - Node-RED integration
  - Local instance on port 1880
  - Flow-based automation capabilities

- **Distribution**
  - Self-hosted web application mode
  - Electron desktop application (Linux, Windows, macOS)
  - AppImage for portable Linux deployment
  - DEB packages for Debian/Ubuntu
  - Windows installer and portable executables
  - macOS DMG and ZIP packages

- **Development**
  - Unified startup script (`start.sh`)
  - Development mode for Electron
  - Automated build pipeline
  - GitHub Actions CI/CD

### Features
- Real-time instrument monitoring
- WebSocket-based data streaming
- Multi-instrument dashboard
- Configurable measurement sources
- Live graph updates with locked frequency during recording
- Independent Y-axis scaling for multiple data sources
- Measurement table with timestamped records
- User-friendly mode dropdowns with display names
- API endpoint tooltips for debugging
- Responsive UI with status indicators

### Technical
- Python 3.8+ backend
- React 18+ frontend
- TypeScript support
- FastAPI with async/await
- WebSocket communication protocol
- Canvas-based graph rendering
- Electron 28+ for desktop apps

## Release Types

- **Major** (x.0.0): Breaking changes, major new features
- **Minor** (0.x.0): New features, backwards compatible
- **Patch** (0.0.x): Bug fixes, minor improvements

## Links
- [Repository](https://github.com/YOUR_ORG/BenchMesh)
- [Documentation](./README.md)
- [Release Process](./.github/RELEASE_PROCESS.md)
