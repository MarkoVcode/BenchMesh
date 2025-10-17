#!/bin/bash
# Script to verify Metrics UI is accessible

echo "🔍 Verifying Metrics WebSocket System..."
echo

# Check if service is running
if ! curl -s http://localhost:57666/ui/ > /dev/null; then
    echo "❌ Service not running on port 57666"
    exit 1
fi
echo "✅ Service is running"

# Check if metrics endpoint exists
if curl -s -o /dev/null -w "%{http_code}" http://localhost:57666/docs | grep -q "200"; then
    echo "✅ API docs accessible"
fi

# Verify metrics in frontend bundle
if curl -s http://localhost:57666/ui/ | grep -q "index-.*\.js"; then
    BUNDLE=$(curl -s http://localhost:57666/ui/ | grep -o 'index-[^"]*\.js' | head -1)
    if curl -s "http://localhost:57666/ui/assets/$BUNDLE" | grep -q "Serial Port Utilization Metrics"; then
        echo "✅ Metrics UI in frontend bundle"
    else
        echo "❌ Metrics UI not found in bundle"
        exit 1
    fi
fi

# Test WebSocket connection
echo
echo "📡 Testing WebSocket connection..."
python3 - << 'PYEOF'
import asyncio
import websockets
import sys

async def test():
    try:
        async with websockets.connect("ws://localhost:57666/ws/metrics") as ws:
            print("✅ WebSocket connected successfully")
            data = await asyncio.wait_for(ws.recv(), timeout=35)
            print("✅ Received metrics data")
            return True
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
PYEOF

if [ $? -eq 0 ]; then
    echo
    echo "🎉 All checks passed!"
    echo
    echo "To view Metrics UI:"
    echo "1. Open: http://localhost:57666"
    echo "2. Click: 📈 Metrics button (next to Documentation)"
    echo "3. View: Real-time metrics updating every 30s"
else
    echo
    echo "❌ Some checks failed"
    exit 1
fi
