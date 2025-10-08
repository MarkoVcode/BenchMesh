# BenchMesh System Startup Guide

## Quick Start

To start the entire BenchMesh system (Backend, Frontend, and Node-RED):

```bash
./start.sh
```

This will launch:
- **BenchMesh API & Frontend** on `http://localhost:57666`
- **Node-RED Automations** on `http://localhost:1880`

Press `Ctrl+C` to stop all services.

## First Time Setup

### 1. Install Python Dependencies

```bash
cd benchmesh-serial-service
pip install -r requirements.txt
cd ..
```

### 2. Install Node.js Dependencies

```bash
npm install
```

### 3. Install Frontend Dependencies

```bash
cd benchmesh-serial-service/frontend
npm ci
cd ../..
```

## Individual Services

### Start Backend Only

```bash
cd benchmesh-serial-service
PYTHONPATH=src uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 57666
```

### Start Node-RED Only

```bash
npm run start:nodered
```

### Start Frontend Development Server

```bash
cd benchmesh-serial-service/frontend
npm run dev
```

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 57666 | http://localhost:57666 |
| API | 57666 | http://localhost:57666/docs |
| Node-RED | 1880 | http://localhost:1880 |

## Node-RED Data

Node-RED configuration and flows are stored in `.node-red/` directory in the repository root.

## Troubleshooting

### Port Already in Use

If you get "address already in use" errors:

```bash
# Check what's using port 57666
lsof -i :57666

# Check what's using port 1880
lsof -i :1880

# Kill the process
kill <PID>
```

### Node-RED Not Starting

```bash
# Check Node-RED logs
cat .node-red/nodered.log

# Test Node-RED manually
./node_modules/.bin/node-red --userDir ./.node-red --port 1880

# Check if Node-RED is installed
ls -la node_modules/.bin/node-red
```

### Frontend Not Building

```bash
cd benchmesh-serial-service/frontend
rm -rf node_modules
npm ci
npm run build
```
