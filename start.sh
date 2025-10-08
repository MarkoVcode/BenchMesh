#!/bin/bash

# BenchMesh Startup Script
# Starts FastAPI backend, Frontend, and Node-RED

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting BenchMesh System..."

# Create node-red data directory if it doesn't exist
mkdir -p .node-red

# Start Node-RED in background using local installation
echo "📡 Starting Node-RED on port 1880..."
./node_modules/.bin/node-red --userDir "$SCRIPT_DIR/.node-red" > .node-red/nodered.log 2>&1 &
NODERED_PID=$!
echo "Node-RED PID: $NODERED_PID"

# Start FastAPI backend with frontend
echo "🔧 Starting BenchMesh API and Frontend..."
cd benchmesh-serial-service
PYTHONPATH=src uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 57666 &
API_PID=$!
echo "API PID: $API_PID"

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 3

echo ""
echo "✅ BenchMesh System Started!"
echo ""
echo "📊 Frontend:  http://localhost:57666"
echo "🔴 Node-RED:  http://localhost:1880"
echo "📡 API:       http://localhost:57666/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap Ctrl+C to stop all services
trap "echo ''; echo '🛑 Stopping BenchMesh...'; kill $NODERED_PID $API_PID 2>/dev/null; exit 0" INT TERM

# Keep script running
wait
