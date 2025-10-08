# BenchMesh Electron Distribution

This document describes how to package and distribute BenchMesh as a standalone desktop application using Electron.

## Overview

BenchMesh can be run in two modes:
1. **Self-hosted**: Traditional web-based deployment using `./start.sh`
2. **Electron App**: Standalone desktop application (Windows, macOS, Linux)

## Prerequisites

### For Development
- Node.js 18+ and npm
- Python 3.8+
- All dependencies installed (see STARTUP.md)

### For Building Electron App
```bash
cd electron
npm install
```

## Development Mode

### Option 1: Self-Hosted (Web-based)
```bash
./start.sh
# Access at http://localhost:57666
```

### Option 2: Electron Development
```bash
# Terminal 1: Start backend services
./start.sh

# Terminal 2: Start Electron in dev mode
cd electron
NODE_ENV=development npm start
```

## Building Electron App

### Build for Current Platform
```bash
cd electron
npm run build
```

### Build for Specific Platforms
```bash
# Linux (AppImage, .deb)
npm run build:linux

# Windows (installer, portable)
npm run build:win

# macOS (DMG, ZIP)
npm run build:mac
```

Built applications will be in `dist/` directory.

## Distribution

### Linux
- **AppImage**: Portable, no installation required
- **DEB Package**: For Debian/Ubuntu systems

### Windows
- **NSIS Installer**: Standard Windows installer
- **Portable**: No installation, run directly

### macOS
- **DMG**: Drag-and-drop installation
- **ZIP**: Compressed archive

## Architecture

```
┌─────────────────────────────────────┐
│     Electron Main Process           │
│  ┌────────────────────────────────┐ │
│  │  • Manages app lifecycle       │ │
│  │  • Spawns Python backend       │ │
│  │  • Spawns Node-RED service     │ │
│  │  • Creates browser window      │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌─────────────┐         ┌──────────────┐
│   Python    │         │   Node-RED   │
│   Backend   │◄────────┤   Service    │
│  (FastAPI)  │         │  (Port 1880) │
│(Port 57666) │         └──────────────┘
└─────────────┘
       │
       ▼
┌──────────────────────┐
│  Electron Renderer   │
│  (React Frontend)    │
│  • Instrument UI     │
│  • Measurements      │
│  • Graphs            │
└──────────────────────┘
```

## Key Files

### `electron/main.js`
- Main Electron process
- Starts Python backend and Node-RED
- Manages application lifecycle
- Handles process cleanup on exit

### `electron/preload.js`
- Security bridge between main and renderer
- Exposes limited APIs to frontend
- Prevents direct Node.js access from renderer

### `electron/package.json`
- Electron-specific dependencies
- Build configuration
- Platform-specific settings

## Packaging Details

### Included in Build
- React frontend (built/minified)
- Python backend source
- Node-RED configuration
- Python dependencies (requirements.txt)

### External Requirements
User must have installed:
- Python 3.8+ (with pip)
- System dependencies for serial communication

### First Run Setup
The app should:
1. Check for Python installation
2. Install Python dependencies: `pip install -r requirements.txt`
3. Start services
4. Open application window

## Configuration

### Backend Port
Default: 57666 (configurable in main.js)

### Node-RED Port
Default: 1880 (configurable in main.js)

### Development Mode
Set `NODE_ENV=development` to:
- Connect to existing dev servers
- Enable DevTools
- Skip service spawning (manual start required)

## Production Considerations

### Auto-Updates (Optional)
Add electron-updater for automatic updates:
```bash
npm install electron-updater
```

### Code Signing (Optional)
For production releases:
- **macOS**: Requires Apple Developer certificate
- **Windows**: Recommended for SmartScreen
- **Linux**: Optional GPG signing

### Installer Customization
Edit `electron/package.json` build section for:
- Custom icons
- License agreements
- Installation directories
- Start menu shortcuts

## Troubleshooting

### Services Not Starting
- Check Python is in PATH
- Verify `requirements.txt` dependencies installed
- Check ports 57666 and 1880 are available

### Blank Window
- Wait 2-3 seconds for services to start
- Check console for backend errors
- Verify frontend built correctly: `cd benchmesh-serial-service/frontend && npm run build`

### Build Fails
- Ensure all dependencies installed
- Check Node.js version (18+)
- Verify Python backend can run standalone

## Comparison: Self-Hosted vs Electron

| Feature | Self-Hosted | Electron App |
|---------|-------------|--------------|
| Installation | Manual setup | Single installer |
| Updates | Git pull | Auto-update capable |
| Access | Any browser | Dedicated window |
| Multi-user | Yes (networked) | Single user |
| Resources | Lighter | ~200MB app |
| Platform | Any with browser | Windows/Mac/Linux |
| Serial Access | Direct | Direct |

## Future Enhancements

1. **Auto-updater**: Implement electron-updater
2. **Tray Icon**: Background operation with system tray
3. **Python Bundling**: Package Python runtime with app (PyInstaller)
4. **Splash Screen**: Loading screen while services start
5. **Service Status**: Visual indicators for backend/Node-RED health
6. **Settings UI**: Configure ports, paths via GUI
