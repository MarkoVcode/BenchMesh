#!/bin/bash

# BenchMesh Electron Development Launcher
# This script starts the backend services and then launches Electron in dev mode

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting BenchMesh in Electron development mode..."
echo "Project root: $PROJECT_ROOT"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $BACKEND_PID $NODERED_PID 2>/dev/null
    wait $BACKEND_PID $NODERED_PID 2>/dev/null
    echo "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Node-RED in background
echo "Starting Node-RED..."
"$PROJECT_ROOT/node_modules/.bin/node-red" --userDir "$PROJECT_ROOT/.node-red" > "$PROJECT_ROOT/.node-red/nodered.log" 2>&1 &
NODERED_PID=$!
echo "Node-RED started (PID: $NODERED_PID)"

# Start Python backend in background
echo "Starting Python backend..."
cd "$PROJECT_ROOT/benchmesh-serial-service"
PYTHONPATH=src uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 57666 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Wait a moment for services to start
sleep 2

# Start Electron
echo "Starting Electron..."
cd "$SCRIPT_DIR"
NODE_ENV=development node_modules/.bin/electron .

# If Electron exits, cleanup
cleanup
