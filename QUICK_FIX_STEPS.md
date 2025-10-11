# Quick Fix: Automation UI Integration

## The Issue
The `/benchmesh/automations` API was returning empty `{}` because it was looking in the wrong context storage location.

## The Fix
Updated `node-red-contrib-benchmesh/nodes/automation.js` to correctly access the node's global context.

## Steps to Test (Do This Now!)

### 1. Restart Node-RED
**Important**: You must restart Node-RED to load the updated custom node code.

```bash
# Stop the current ./start.sh (Ctrl+C in that terminal)
# Or kill Node-RED specifically:
pkill -f node-red

# Then start again:
cd /home/marek/project/BenchMesh
./start.sh
```

### 2. Import the Example Flow
1. Open Node-RED: http://localhost:1880
2. Menu (≡) → Import → Select file
3. Navigate to: `/home/marek/project/BenchMesh/docs/node-red/examples/do-not-allow-overcharge.json`
4. Click "Import"
5. You'll see a new tab: "Overcharge Protection"
6. Click "Deploy" (top right, red button)

### 3. Verify the Automation is Tracked
```bash
curl -s http://localhost:1880/benchmesh/automations | jq
```

**Expected output:**
```json
{
  "automation_node": {
    "id": "automation_node",
    "name": "Overcharge Protection",
    "frequency": 1000,
    "enabled": true,
    "lastTrigger": 1234567890
  }
}
```

If you see this, the fix worked! ✅

### 4. Check the UI
1. Refresh your browser: http://localhost:57666/ui/
2. Hard refresh to clear cache: **Ctrl+Shift+R**
3. Wait 5-10 seconds for the UI to poll
4. You should now see:
   - Button: 🔴 RED
   - Badge: **"1/1"** (1 running out of 1 total)
   - Hover tooltip: "1 automations running - Click to open Node-RED"

### 5. Test Stop/Start
1. In Node-RED, find the "Battery Protection Timer" node
2. Click the small button on the node itself (it will toggle)
3. Node should turn RED (stopped)
4. Wait 5 seconds
5. Refresh browser
6. Badge should show: **"0/1"**
7. Click the button again to start
8. Node turns GREEN (running)
9. Wait 5 seconds, refresh
10. Badge should show: **"1/1"** again

## Troubleshooting

### Still Returns Empty {}
**Solution**: Make sure you:
1. Actually restarted Node-RED (not just redeployed)
2. Imported and deployed the new example flow
3. Waited a few seconds after deploy

### Can't Find Example Flow File
```bash
ls -la /home/marek/project/BenchMesh/docs/node-red/examples/do-not-allow-overcharge.json
```

Should show the file. If not, it was created earlier - check git status.

### Node-RED Won't Start
Check logs:
```bash
cd /home/marek/project/BenchMesh
./start.sh 2>&1 | grep -i error
```

### UI Still Shows No Badge
1. Open browser console (F12)
2. Look for: `[BenchMesh] Automations: {total: X, running: Y}`
3. If total is 0, the API still isn't working
4. If you see the log with correct numbers but no badge, there's a React rendering issue

## Quick Verification Script

Run this after restarting Node-RED and importing the flow:

```bash
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
    echo "📊 Badge: (none)"
fi

echo -e "\n3. Now refresh your browser!"
echo "   http://localhost:57666/ui/"
echo "   Press Ctrl+Shift+R to hard refresh"
```

Save as `verify_automation.sh`, make executable with `chmod +x`, then run `./verify_automation.sh`

## Success Criteria

✅ Automation API returns JSON with automation data
✅ UI button shows RED when automation running
✅ Badge shows "1/1"
✅ Tooltip shows correct information
✅ Button toggles colors when automation stops/starts

Once all these work, the integration is complete!
