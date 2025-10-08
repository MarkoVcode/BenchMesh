# BenchMesh Distribution Guide

## Quick Start

BenchMesh offers two distribution methods:

### 1. Self-Hosted Web Application (Recommended for Development)
```bash
./start.sh
# Access at http://localhost:57666
```

### 2. Electron Desktop Application
```bash
# Development
npm run electron:dev

# Build for distribution
npm run electron:build        # Current platform
npm run electron:build:linux  # Linux (AppImage, .deb)
npm run electron:build:win    # Windows (installer, portable)
npm run electron:build:mac    # macOS (DMG, ZIP)
```

## Setup Instructions

### Initial Setup (Both Methods)

1. **Install Node.js dependencies:**
   ```bash
   npm install
   cd benchmesh-serial-service/frontend
   npm ci
   cd ../..
   ```

2. **Install Python dependencies:**
   ```bash
   cd benchmesh-serial-service
   pip install -r requirements.txt
   cd ..
   ```

### Self-Hosted Mode

**Start all services:**
```bash
./start.sh
```

**Services will be available at:**
- Frontend & API: http://localhost:57666
- API Docs: http://localhost:57666/docs
- Node-RED: http://localhost:1880

**Stop services:**
Press `Ctrl+C`

### Electron Desktop App Mode

#### Development
```bash
npm run electron:dev
```
This launches a desktop window with the application.

#### Building for Distribution

**Before building, ensure frontend is built:**
```bash
cd benchmesh-serial-service/frontend
npm run build
cd ../..
```

**Build the application:**
```bash
# For your current platform
npm run electron:build

# For specific platforms
npm run electron:build:linux
npm run electron:build:win
npm run electron:build:mac
```

**Built applications will be in:** `dist/`

## Distribution Packages

### Linux
- **AppImage**: `dist/BenchMesh-1.0.0.AppImage`
  - Portable, no installation needed
  - Run: `chmod +x BenchMesh-1.0.0.AppImage && ./BenchMesh-1.0.0.AppImage`

- **DEB Package**: `dist/BenchMesh_1.0.0_amd64.deb`
  - For Debian/Ubuntu systems
  - Install: `sudo dpkg -i BenchMesh_1.0.0_amd64.deb`

### Windows
- **Installer**: `dist/BenchMesh Setup 1.0.0.exe`
  - Standard Windows installer
  - Includes uninstaller

- **Portable**: `dist/BenchMesh 1.0.0.exe`
  - No installation required
  - Run directly from USB or any location

### macOS
- **DMG**: `dist/BenchMesh-1.0.0.dmg`
  - Drag-and-drop installation

- **ZIP**: `dist/BenchMesh-1.0.0-mac.zip`
  - Extract and run

## System Requirements

### Runtime Requirements
- **Operating System**: Linux, Windows 10+, or macOS 10.14+
- **Python**: 3.8 or higher
- **Node.js**: 18 or higher (for development only)
- **Serial Port Access**: For instrument communication

### Build Requirements (Development)
- All runtime requirements
- Git
- npm and Node.js 18+
- Platform-specific build tools:
  - **Linux**: Standard build tools (`build-essential`)
  - **Windows**: Visual Studio Build Tools or Visual Studio
  - **macOS**: Xcode Command Line Tools

## Deployment Scenarios

### Scenario 1: Laboratory Workstation (Self-Hosted)
**Use Case**: Single machine, local access
```bash
./start.sh
# Access locally at http://localhost:57666
```

### Scenario 2: Network Access (Self-Hosted)
**Use Case**: Multiple users, remote access
```bash
# Start services
./start.sh

# Access from other machines at:
# http://<server-ip>:57666
```

### Scenario 3: Portable Instrument Setup (Electron)
**Use Case**: Laptop/portable setup, no installation
```bash
# Use Linux AppImage or Windows Portable
./BenchMesh-1.0.0.AppImage
```

### Scenario 4: Production Desktop App (Electron)
**Use Case**: Installed desktop application
```bash
# Use platform installers
# Windows: BenchMesh Setup 1.0.0.exe
# Linux: BenchMesh_1.0.0_amd64.deb
# macOS: BenchMesh-1.0.0.dmg
```

## Architecture Comparison

### Self-Hosted (Web)
```
┌─────────────┐
│   Browser   │ ← User interface
└──────┬──────┘
       │ HTTP
┌──────▼────────┐
│  FastAPI      │ ← Python backend (Port 57666)
│  + Frontend   │
└───────────────┘
       │
┌──────▼────────┐
│   Node-RED    │ ← Automation (Port 1880)
└───────────────┘
```

### Electron (Desktop)
```
┌─────────────────────┐
│  Electron Window    │ ← Desktop app
│  ┌───────────────┐  │
│  │  React UI     │  │
│  └───────┬───────┘  │
└──────────┼──────────┘
           │ IPC
┌──────────▼──────────┐
│  Electron Main      │
│  ├─ Python Backend  │ ← Spawned process
│  └─ Node-RED        │ ← Spawned process
└─────────────────────┘
```

## Security Considerations

### Self-Hosted Mode
- ⚠️ No built-in authentication
- ⚠️ Accessible to anyone on network
- ✅ Can add reverse proxy (nginx) with auth
- ✅ Use firewall to restrict access

### Electron Mode
- ✅ Local-only by default
- ✅ Context isolation enabled
- ✅ No remote code execution
- ⚠️ User must trust instrument drivers

## Troubleshooting

### Self-Hosted Issues

**Port already in use:**
```bash
# Find process using port
lsof -i :57666
lsof -i :1880

# Kill the process
kill <PID>
```

**Python backend not starting:**
```bash
# Check Python version
python3 --version

# Reinstall dependencies
cd benchmesh-serial-service
pip install -r requirements.txt --force-reinstall
```

### Electron Issues

**Build fails:**
```bash
# Ensure frontend is built first
cd benchmesh-serial-service/frontend
npm run build

# Clean and rebuild
cd ../../electron
rm -rf node_modules
npm install
npm run build
```

**Blank window on startup:**
- Wait 2-3 seconds for services to start
- Check if Python is installed: `python3 --version`
- Check logs in: `.node-red/nodered.log`

**Services not starting in packaged app:**
- Ensure Python is in system PATH
- Check Python dependencies are installed
- Verify ports 57666 and 1880 are available

## Advanced Configuration

### Custom Ports
Edit `electron/main.js`:
```javascript
// Change backend port
const backendPort = 57666  // Change this

// Change Node-RED port
const nodeRedPort = 1880   // Change this
```

### Add Custom Icons
1. Create icons: `electron/assets/icon.png` (512x512)
2. For platform-specific:
   - Windows: `icon.ico`
   - macOS: `icon.icns`
   - Linux: `icon.png`

### Code Signing (Production)
For production releases, sign your apps:

**macOS:**
```bash
# Requires Apple Developer certificate
export CSC_LINK="path/to/certificate.p12"
export CSC_KEY_PASSWORD="certificate-password"
npm run electron:build:mac
```

**Windows:**
```bash
# Requires code signing certificate
npm run electron:build:win
```

## Distribution Checklist

Before distributing:

- [ ] Frontend built: `cd benchmesh-serial-service/frontend && npm run build`
- [ ] Python dependencies listed in `requirements.txt`
- [ ] Node-RED flows tested
- [ ] All instrument drivers included
- [ ] README and documentation updated
- [ ] Version number updated in `package.json`
- [ ] Icons and branding added
- [ ] Tested on target platforms
- [ ] Code signed (production only)

## Support & Updates

### Self-Hosted Updates
```bash
git pull
npm install
cd benchmesh-serial-service/frontend
npm ci
npm run build
cd ../..
./start.sh
```

### Electron Updates
- Download new version
- Install over old version (settings preserved)
- Or implement auto-updater (see ELECTRON.md)

## License & Distribution

See LICENSE file for distribution terms.

For commercial distribution, ensure:
- All dependencies are compatible
- Third-party licenses included
- Attribution provided
- Code signing completed
