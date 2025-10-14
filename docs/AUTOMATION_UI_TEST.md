# BenchMesh Automation UI Integration - Test Plan

## Current Status

The UI has been updated to show automation status with the following logic:

### Button Color Logic:
- **🔴 RED** = Any automations are running (active monitoring needed)
- **🟢 GREEN** = All automations stopped (safe/idle state)

### Counter Display:
- Shows **"X/Y"** badge on the button
  - X = number of running automations
  - Y = total number of automations
- Only shows when Y > 0 (automations exist)

## Why Button is Currently RED

Your button shows RED because you have **3 active inject nodes** with repeat intervals in Node-RED. These are the old-style inject nodes from the existing flow. The custom BenchMesh automation nodes are installed but not yet deployed.

## Testing Steps

### Step 1: Verify Frontend is Loaded
1. Refresh browser at http://localhost:57666/ui/
2. Hard refresh (Ctrl+Shift+R) to clear cache
3. Open browser console (F12)
4. Look for log: `[BenchMesh] Automations: {total: 0, running: 0, automations: {}}`
5. Button should be **🔴 RED** (because inject nodes are active)
6. No counter badge should appear (because no BenchMesh automation nodes yet)

### Step 2: Check Current Node-RED State
```bash
# Count active inject nodes (old style)
curl -s http://localhost:1880/flows | jq '[.[] | select(.type == "inject" and .repeat)] | length'
# Should return: 3

# Check BenchMesh automations (new style)
curl -s http://localhost:1880/benchmesh/automations
# Should return: {}
```

### Step 3: Verify Custom Nodes are Installed
1. Open Node-RED: http://localhost:1880
2. Look in left sidebar for "BenchMesh" category
3. You should see 6 nodes:
   - benchmesh-automation
   - benchmesh-dmm
   - benchmesh-ell
   - benchmesh-psu
   - benchmesh-threshold
   - benchmesh-instrument

**If nodes don't appear:**
```bash
# Restart Node-RED
cd /home/marek/project/BenchMesh
# Stop current instance (Ctrl+C on the terminal running ./start.sh)
# Start again
./start.sh
```

### Step 4: Import Example Flow with Custom Nodes
1. In Node-RED: Menu → Import → Select file
2. Choose: `/home/marek/project/BenchMesh/docs/node-red/examples/do-not-allow-overcharge.json`
3. Click "Import"
4. You'll see a new tab: "Overcharge Protection"
5. Click "Deploy" button (top right)

### Step 5: Verify Automation Tracking
```bash
# Check automations API
curl -s http://localhost:1880/benchmesh/automations | jq
```

Expected output:
```json
{
  "automation_node": {
    "id": "automation_node",
    "name": "Overcharge Protection",
    "frequency": 1000,
    "enabled": true,
    "lastTrigger": 1699999999999
  }
}
```

### Step 6: Check UI Updates
1. Wait 5 seconds (UI polls every 5 seconds)
2. Refresh browser if needed
3. Check browser console for: `[BenchMesh] Automations: {total: 1, running: 1, ...}`
4. Button should show **🔴 RED** with badge **"1/1"**
5. Hover over button - tooltip should say: "1 automations running - Click to open Node-RED"

### Step 7: Test Stop Automation
1. In Node-RED, click the button on the "Battery Protection Timer" node
2. Node should turn RED (stopped)
3. Wait 5 seconds
4. UI button should remain **🔴 RED** (because old inject nodes still active)
5. Badge should show **"0/1"**

### Step 8: Disable Old Inject Nodes
1. In Node-RED, go to the old flow tab
2. Double-click each inject node with repeat
3. Disable them or delete the old flow
4. Deploy
5. Wait 5 seconds
6. UI button should now be **🟢 GREEN** with badge **"0/1"**
7. Tooltip: "All 1 automations stopped"

### Step 9: Test Start Automation
1. Click button on "Battery Protection Timer" node in Node-RED
2. Node should turn GREEN (running)
3. Wait 5 seconds
4. UI button should be **🔴 RED** with badge **"1/1"**
5. Tooltip: "1 automations running"

## Troubleshooting

### Button Always RED, No Counter
**Cause**: Old inject nodes are running, no BenchMesh automations deployed
**Fix**: Import and deploy the example flow with BenchMesh automation nodes

### Counter Shows "0/0"
**Cause**: Custom nodes not installed or Node-RED not restarted
**Fix**:
```bash
cd /home/marek/project/BenchMesh/.node-red
npm install /home/marek/project/BenchMesh/node-red-contrib-benchmesh
# Restart Node-RED
```

### Counter Doesn't Update
**Cause**: Browser cache or polling not working
**Fix**:
- Hard refresh (Ctrl+Shift+R)
- Check console for errors
- Verify Node-RED is accessible at port 1880

### CORS Errors in Console
**Cause**: Browser security blocking requests
**Fix**: Both services must use same hostname (localhost)
- BenchMesh UI: http://localhost:57666
- Node-RED: http://localhost:1880

### API Returns 404
**Cause**: Custom nodes not properly loaded
**Fix**: Check Node-RED startup logs for errors loading benchmesh nodes

## Expected Behavior Summary

| State | Old Inject Nodes | BenchMesh Automations | Button Color | Counter | Tooltip |
|-------|-----------------|---------------------|--------------|---------|---------|
| Initial | 3 running | 0/0 | 🔴 RED | (none) | "No automations configured" |
| After import | 3 running | 1 stopped | 🔴 RED | 0/1 | "All 1 automations stopped" |
| All running | 3 running | 1 running | 🔴 RED | 1/1 | "1 automations running" |
| Clean slate | 0 running | 0 stopped | 🟢 GREEN | (none) | "No automations configured" |
| Only BenchMesh stopped | 0 running | 1 stopped | 🟢 GREEN | 0/1 | "All 1 automations stopped" |
| Only BenchMesh running | 0 running | 1 running | 🔴 RED | 1/1 | "1 automations running" |

## Quick Test Script

```bash
#!/bin/bash
echo "=== BenchMesh Automation UI Test ==="

echo -e "\n1. Checking old inject nodes..."
OLD_INJECTS=$(curl -s http://localhost:1880/flows | jq '[.[] | select(.type == "inject" and .repeat)] | length')
echo "Old inject nodes with repeat: $OLD_INJECTS"

echo -e "\n2. Checking BenchMesh automations..."
curl -s http://localhost:1880/benchmesh/automations | jq

echo -e "\n3. Expected UI state:"
AUTOMATIONS=$(curl -s http://localhost:1880/benchmesh/automations | jq 'length')
RUNNING=$(curl -s http://localhost:1880/benchmesh/automations | jq '[.[] | select(.enabled == true)] | length')

if [ "$OLD_INJECTS" -gt 0 ] || [ "$RUNNING" -gt 0 ]; then
    echo "Button: 🔴 RED (active automations)"
else
    echo "Button: 🟢 GREEN (all stopped)"
fi

if [ "$AUTOMATIONS" -gt 0 ]; then
    echo "Counter: $RUNNING/$AUTOMATIONS"
else
    echo "Counter: (none - no automations configured)"
fi

echo -e "\n4. Now refresh your browser and check!"
echo "   URL: http://localhost:57666/ui/"
echo "   Open console (F12) to see logs"
```

Save this to `scripts/test-automation-ui.sh` and run it to check the current state!
