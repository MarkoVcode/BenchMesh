#!/bin/bash
echo "🔍 Checking automation integration..."

echo -e "\n1. Testing API endpoint..."
RESPONSE=$(curl -s http://localhost:1880/benchmesh/automations)
echo "$RESPONSE" | jq

COUNT=$(echo "$RESPONSE" | jq 'length')
if [ "$COUNT" -gt 0 ]; then
    echo "✅ API working! Found $COUNT automation(s)"
else
    echo "❌ API returns empty - did you import and deploy the flow?"
    echo "   Steps:"
    echo "   1. Restart Node-RED (important!)"
    echo "   2. Import: /home/marek/project/BenchMesh/docs/node-red/examples/do-not-allow-overcharge.json"
    echo "   3. Click Deploy"
    echo "   4. Run this script again"
fi

echo -e "\n2. Expected UI state:"
RUNNING=$(echo "$RESPONSE" | jq '[.[] | select(.enabled == true)] | length')
OLD_INJECTS=$(curl -s http://localhost:1880/flows | jq '[.[] | select(.type == "inject" and .repeat)] | length')

if [ "$OLD_INJECTS" -gt 0 ] || [ "$RUNNING" -gt 0 ]; then
    echo "🔴 Button: RED"
else
    echo "🟢 Button: GREEN"
fi

if [ "$COUNT" -gt 0 ]; then
    echo "📊 Badge: $RUNNING/$COUNT"
else
    echo "📊 Badge: (none - no automations)"
fi

echo -e "\n3. Detailed info:"
echo "   - Old inject nodes running: $OLD_INJECTS"
echo "   - BenchMesh automations total: $COUNT"
echo "   - BenchMesh automations running: $RUNNING"

echo -e "\n4. Now refresh your browser!"
echo "   URL: http://localhost:57666/ui/"
echo "   Press Ctrl+Shift+R to hard refresh"
echo "   Open console (F12) to see logs"
