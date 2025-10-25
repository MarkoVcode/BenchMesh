#!/bin/bash

# BenchMesh Startup Script
# Starts FastAPI backend, Frontend, and Node-RED
# Usage: ./start.sh [--uibuild] [--electron]
#   --uibuild: Build the frontend UI before starting
#   --electron: Build and run in Electron wrapper
export BM_UNIFIED_POLL_INTERVAL=50
export BM_UNIFIED_POLLING=true
export BM_MAX_QUEUE_DEPTH=10

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Initialize user data directory for persistence
USER_DATA_DIR="$HOME/.benchmesh"
CONFIG_PATH="$USER_DATA_DIR/config.yaml"
NODE_RED_DIR="$USER_DATA_DIR/node-red"
LOGS_DIR="$USER_DATA_DIR/logs"

echo "==========================================="
echo "Initializing BenchMesh User Data"
echo "==========================================="
echo "User data directory: $USER_DATA_DIR"

# Create user data directory structure
mkdir -p "$USER_DATA_DIR"
mkdir -p "$NODE_RED_DIR"
mkdir -p "$LOGS_DIR"

# Copy default config.yaml if it doesn't exist
if [ ! -f "$CONFIG_PATH" ]; then
  echo "Copying default config.yaml to $CONFIG_PATH"
  cp "benchmesh-serial-service/config.yaml" "$CONFIG_PATH"
else
  echo "Using existing config at $CONFIG_PATH"
fi

# Create symlink to custom Node-RED nodes
CUSTOM_NODES_SOURCE="$(pwd)/node-red-contrib-benchmesh"
CUSTOM_NODES_LINK="$NODE_RED_DIR/node_modules/node-red-contrib-benchmesh"

mkdir -p "$NODE_RED_DIR/node_modules"

if [ -d "$CUSTOM_NODES_SOURCE" ]; then
  if [ ! -e "$CUSTOM_NODES_LINK" ]; then
    ln -s "$CUSTOM_NODES_SOURCE" "$CUSTOM_NODES_LINK"
    echo "Created symlink to custom Node-RED nodes"
  fi
else
  echo "Warning: Custom Node-RED nodes not found at $CUSTOM_NODES_SOURCE"
fi

echo "User data initialization complete"
echo "==========================================="
echo ""

# Export environment variables for backend services
export BENCHMESH_CONFIG="$CONFIG_PATH"
export BENCHMESH_DATA_DIR="$USER_DATA_DIR"

# Parse command line arguments
BUILD_UI=false
ELECTRON_MODE=false
for arg in "$@"; do
  case $arg in
    --uibuild)
      BUILD_UI=true
      shift
      ;;
    --electron)
      ELECTRON_MODE=true
      BUILD_UI=true  # Always build UI for Electron
      shift
      ;;
  esac
done

echo "🚀 Starting BenchMesh System..."

# Build frontend if --uibuild flag is provided
if [ "$BUILD_UI" = true ]; then
  echo "🔨 Building frontend UI..."
  cd benchmesh-serial-service/frontend
  npm ci --quiet
  npm run build
  cd "$SCRIPT_DIR"
  echo "✅ Frontend build complete"
else
  echo "⏭️  Skipping UI build (use --uibuild to rebuild)"
fi

# Start Node-RED in background using local installation
echo "📡 Starting Node-RED on port 1880..."
echo "Node-RED user directory: $NODE_RED_DIR"
./node_modules/.bin/node-red --userDir "$NODE_RED_DIR" > "$LOGS_DIR/nodered.log" 2>&1 &
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

# If in Electron mode, launch Electron app
if [ "$ELECTRON_MODE" = true ]; then
  echo "🖥️  Launching Electron application..."
  echo ""
  cd "$SCRIPT_DIR/electron"
  npm start &
  ELECTRON_PID=$!

  # Trap Ctrl+C to stop all services including Electron
  trap "echo ''; echo '🛑 Stopping BenchMesh...'; kill $ELECTRON_PID $NODERED_PID $API_PID 2>/dev/null; exit 0" INT TERM

  # Wait for Electron to close
  wait $ELECTRON_PID

  # Clean up backend services when Electron closes
  echo ""
  echo "🛑 Stopping backend services..."
  kill $NODERED_PID $API_PID 2>/dev/null
else
  # Normal browser mode
  echo "📊 Frontend:  http://localhost:57666/ui"
  echo "🔴 Node-RED:  http://localhost:1880"
  echo "📡 API Docs:  http://localhost:57666/docs"
  echo ""
  echo "Note: Visit http://localhost:57666 to auto-redirect to the frontend"
  echo ""
  echo "Press Ctrl+C to stop all services"
  echo ""

  # Trap Ctrl+C to stop all services
  trap "echo ''; echo '🛑 Stopping BenchMesh...'; kill $NODERED_PID $API_PID 2>/dev/null; exit 0" INT TERM

  # Keep script running
  wait
fi
