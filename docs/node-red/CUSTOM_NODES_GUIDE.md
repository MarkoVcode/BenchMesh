# BenchMesh Custom Node-RED Nodes - Installation & Usage Guide

## Overview

BenchMesh provides custom Node-RED nodes that make instrument automation easier and more intuitive. These nodes integrate directly with BenchMesh instruments and provide individual automation control without needing to redeploy flows.

## Key Features

### 1. **BenchMesh Automation Node** - The Game Changer
Replace standard inject nodes with controllable automation nodes that can be started/stopped individually:
- ✅ Start/stop without redeploying flows
- ✅ Visual status indication (green = running, red = stopped)
- ✅ Control from Node-RED UI, HTTP API, or BenchMesh UI
- ✅ Tracked globally for monitoring
- ⚠️ **Safety First**: All automations start DISABLED by default - you must manually start them after deployment

### 2. **Instrument-Specific Nodes**
- **DMM (Digital Multimeter)**: Read measurements with auto-parsing
- **ELL (Electronic Load)**: Control loads with visual feedback
- **PSU (Power Supply)**: Query and control power supplies
- **Threshold**: Easy value comparison for safety checks
- **Generic Instrument**: For any custom API calls

### 3. **Integration with BenchMesh UI**
The main UI shows:
- Total number of automations defined
- Number of currently running automations
- Real-time status updates

## Installation

### Step 1: Navigate to Node-RED directory
```bash
cd /home/marek/project/BenchMesh/.node-red
```

### Step 2: Install the package
```bash
npm install /home/marek/project/BenchMesh/node-red-contrib-benchmesh
```

### Step 3: Restart Node-RED
If running manually:
```bash
# Stop current Node-RED (Ctrl+C)
# Start again
node-red
```

If running via start.sh, just restart the script.

### Step 4: Verify Installation
1. Open Node-RED at http://localhost:1880
2. Look for "BenchMesh" category in the node palette (left sidebar)
3. You should see 6 new nodes:
   - 🎯 benchmesh-automation
   - 📊 benchmesh-dmm
   - ⚡ benchmesh-ell
   - 🔌 benchmesh-psu
   - ⚖️ benchmesh-threshold
   - 🔧 benchmesh-instrument

## Quick Start Example

### Create an Overcharge Protection Automation

**Goal**: Monitor voltage and turn on electronic load if voltage exceeds 5V

#### Using Standard Nodes (Old Way):
```
[Inject: 1s] → [HTTP Request to DMM] → [Function: parse] → [Switch: >5V?] → [HTTP Request to ELL]
```
❌ Requires programming
❌ Can't stop without redeploying
❌ Hard to understand

#### Using BenchMesh Nodes (New Way):
```
[Automation: 1s] → [DMM dmm-1] → [Threshold >5V] → [ELL ON/OFF]
```
✅ No programming needed
✅ Stop/start with one click
✅ Clear visual flow

### Step-by-Step Instructions:

1. **Add Automation Node**
   - Drag `benchmesh-automation` to canvas
   - Double-click to configure:
     - Automation Name: "Overcharge Protection"
     - Frequency: 1000 (1 second)
     - Start Enabled: ☐ (leave unchecked - automations are OFF by default for safety)
   - Deploy
   - **After deployment, manually start the automation** by clicking its button or using the BenchMesh UI

2. **Add DMM Node**
   - Drag `benchmesh-dmm` to canvas
   - Configure:
     - Device ID: dmm-1
     - Channel: 1
     - Operation: query_measurement
   - Connect automation output to DMM input

3. **Add Threshold Node**
   - Drag `benchmesh-threshold` to canvas
   - Configure:
     - Property: msg.value
     - Comparison: Greater than (>)
     - Threshold: 5
   - Connect DMM output to threshold input

4. **Add ELL Control Nodes**
   - Drag two `benchmesh-ell` nodes
   - First one (for high voltage):
     - Device ID: eol-1
     - Channel: 1
     - Operation: set_input
     - Value: ON
   - Second one (for safe voltage):
     - Same settings but Value: OFF
   - Connect threshold output 1 (above) to first ELL
   - Connect threshold output 2 (below) to second ELL

5. **Deploy and Test**
   - Click Deploy button
   - Watch the automation node status turn green
   - DMM node will show current voltage
   - Threshold will show comparison result
   - ELL nodes will show ON/OFF state

6. **Control the Automation**
   - Click the button on the automation node to toggle
   - Or open BenchMesh UI to see automation count
   - Or use HTTP API: `POST http://localhost:1880/benchmesh/automations/{id}/toggle`

## Migration from Existing Flows

If you have existing flows using inject + HTTP request nodes:

### Before:
```javascript
[inject: 1s repeat]
  ↓
[http request: GET http://localhost:57666/instruments/DMM/dmm-1/1/query_measurement]
  ↓
[function: var voltage = parseFloat(msg.payload.value); ...]
  ↓
[switch: > 5]
  ↓
[http request: POST http://localhost:57666/instruments/ELL/eol-1/1/set_input/ON]
```

### After:
```
[Automation: "Voltage Monitor" 1s]
  ↓
[DMM: dmm-1, ch1]
  ↓
[Threshold: > 5V]
  ↓
[ELL: eol-1, ON]
```

**Benefits:**
- 70% fewer nodes
- No JavaScript code
- Individually controllable
- Self-documenting

## API Reference

### Get All Automations
```bash
curl http://localhost:1880/benchmesh/automations
```

Response:
```json
{
  "abc123": {
    "id": "abc123",
    "name": "Overcharge Protection",
    "frequency": 1000,
    "enabled": true,
    "lastTrigger": 1699999999999
  }
}
```

### Control Automation
```bash
# Start
curl -X POST http://localhost:1880/benchmesh/automations/{id}/start

# Stop
curl -X POST http://localhost:1880/benchmesh/automations/{id}/stop

# Toggle
curl -X POST http://localhost:1880/benchmesh/automations/{id}/toggle
```

## Best Practices

1. **Always use Automation nodes** instead of inject nodes for recurring tasks
2. **Give descriptive names** to automations (shows in UI)
3. **Use instrument-specific nodes** instead of generic HTTP requests
4. **Use threshold nodes** for simple comparisons
5. **Test with automation disabled** first, then enable
6. **Add debug nodes** during development to see message flow
7. **Use comments** to document complex logic

## Troubleshooting

### Nodes don't appear after installation
```bash
# Check installation
cd /home/marek/project/BenchMesh/.node-red
npm list node-red-contrib-benchmesh

# Reinstall if needed
npm uninstall node-red-contrib-benchmesh
npm install /home/marek/project/BenchMesh/node-red-contrib-benchmesh

# Restart Node-RED completely
```

### Automation doesn't start
- Check node status indicator (red = error)
- Verify BenchMesh backend is running (http://localhost:57666)
- Check API Base URL in node configuration
- Look for errors in Node-RED debug panel

### Can't stop automation
- Make sure flow is deployed (not just configured)
- Check browser console for errors
- Try using HTTP API directly to test

### UI doesn't show automation count
- Verify Node-RED is accessible at port 1880
- Check browser network tab for CORS errors
- Ensure frontend can reach Node-RED
- Wait 5 seconds for next poll cycle

## Examples Library

See `/docs/node-red/examples/` for ready-to-import flows:
- `do-not-allow-overcharge.json` - Battery protection example
- (More examples to be added)

## Advanced Usage

### Dynamic Configuration
You can override node settings via message properties:

```javascript
// Override DMM device at runtime
msg.deviceId = 'dmm-2';
msg.channel = '2';
// Send to DMM node
```

### Chaining Automations
```
[Automation A] → [DMM] → [Threshold] → [Automation B: trigger input]
                                     ↓
                                   [ELL]
```

### Conditional Automation Control
```
[Automation] → [DMM] → [Function: if (value > 10) return {payload: 'stop'}] → [Automation: control itself]
```

## Support

- GitHub Issues: https://github.com/yourusername/benchmesh/issues
- Documentation: `/docs/`
- Examples: `/docs/node-red/examples/`

## Version History

- **v1.0.0**: Initial release
  - 6 custom nodes
  - Automation control API
  - UI integration
