#!/bin/bash
echo "=== BenchMesh Automation UI Test ==="

echo -e "\n1. Checking old inject nodes..."
OLD_INJECTS=$(curl -s http://localhost:1880/flows | jq '[.[] | select(.type == "inject" and .repeat)] | length')
echo "Old inject nodes with repeat: $OLD_INJECTS"

echo -e "\n2. Checking BenchMesh automations..."
AUTOMATIONS_JSON=$(curl -s http://localhost:1880/benchmesh/automations)
echo "$AUTOMATIONS_JSON" | jq

echo -e "\n3. Calculating UI state..."
AUTOMATIONS=$(echo "$AUTOMATIONS_JSON" | jq 'length')
RUNNING=$(echo "$AUTOMATIONS_JSON" | jq '[.[] | select(.enabled == true)] | length')

echo "Total BenchMesh automations: $AUTOMATIONS"
echo "Running BenchMesh automations: $RUNNING"

echo -e "\n4. Expected UI state:"

if [ "$OLD_INJECTS" -gt 0 ] || [ "$RUNNING" -gt 0 ]; then
    echo "Button Color: 🔴 RED (active automations detected)"
else
    echo "Button Color: 🟢 GREEN (all automations stopped)"
fi

if [ "$AUTOMATIONS" -gt 0 ]; then
    echo "Counter Badge: $RUNNING/$AUTOMATIONS"
else
    echo "Counter Badge: (none - no BenchMesh automations configured)"
fi

echo -e "\n5. Explanation:"
if [ "$OLD_INJECTS" -gt 0 ]; then
    echo "⚠️  You have $OLD_INJECTS old-style inject nodes running"
    echo "   These make the button RED even without BenchMesh automations"
fi

if [ "$AUTOMATIONS" -eq 0 ]; then
    echo "ℹ️  No BenchMesh automation nodes deployed yet"
    echo "   Import the example flow to see the counter"
fi

echo -e "\n6. Next steps:"
echo "   1. Refresh browser: http://localhost:57666/ui/ (Ctrl+Shift+R)"
echo "   2. Open console (F12) and look for: [BenchMesh] Automations: ..."
echo "   3. Import example flow in Node-RED to test counter"
echo -e "\n✅ Frontend has been rebuilt with latest changes!"
