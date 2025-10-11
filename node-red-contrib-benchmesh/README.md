# node-red-contrib-benchmesh

Custom Node-RED nodes for BenchMesh instrument control and test automation.

## Overview

This package provides specialized nodes that integrate seamlessly with the BenchMesh instrument control system, making it easy to create test automations without programming knowledge.

## Installation

### Local Development
```bash
cd /home/marek/project/BenchMesh/.node-red
npm install /home/marek/project/BenchMesh/node-red-contrib-benchmesh
```

### From npm (when published)
```bash
cd ~/.node-red
npm install node-red-contrib-benchmesh
```

After installation, restart Node-RED to load the new nodes.

## Available Nodes

### 🎯 BenchMesh Automation
**The core node for creating controllable automations**

- Replaces standard inject nodes with start/stop control
- Individual enable/disable without redeploying flows
- Visible status indication (green = running, red = stopped)
- Can be controlled from:
  - Button on the node itself
  - Input messages ('start', 'stop', 'toggle')
  - HTTP API
  - BenchMesh main UI

**Example Usage:**
```
[Automation: 1s] → [DMM Read] → [Threshold > 5V] → [ELL ON/OFF]
```

### 📊 BenchMesh DMM (Digital Multimeter)
Read voltage, current, or resistance measurements from DMM instruments.

- Auto-parses measurement values
- Displays current reading in node status
- Outputs both full response and parsed numeric value

### ⚡ BenchMesh ELL (Electronic Load)
Control electronic loads for battery testing, power supply testing, etc.

- Turn load ON/OFF
- Set operating mode (CC, CV, CP, CR)
- Set current/voltage/power limits
- Visual status indication

### 🔌 BenchMesh PSU (Power Supply)
Query and control power supply units.

- Read voltage/current
- Set voltage/current
- Control output state
- Supports multi-channel PSUs

### ⚖️ BenchMesh Threshold
Simple threshold comparison for safety checks and control logic.

- Compare values against thresholds
- Visual pass/fail indication
- Two outputs: above/below threshold
- Much easier than using switch nodes

### 🔧 BenchMesh Instrument (Generic)
Generic node for any BenchMesh instrument API call.

- Use when specific node doesn't exist
- Flexible path and method configuration
- Good for experimental or custom instruments

## Example Flow: Overcharge Protection

```
┌─────────────────┐
│ Automation: 1s  │───┐
│ (Start/Stop)    │   │
└─────────────────┘   │
                      ▼
              ┌───────────────┐
              │ DMM Read      │
              │ dmm-1, Ch 1   │
              └───────┬───────┘
                      │ msg.value
                      ▼
              ┌───────────────┐
              │ Threshold     │
              │ > 5V          │
              └───┬───────┬───┘
                  │       │
        Above ────┘       └──── Below
                  │               │
                  ▼               ▼
          ┌──────────────┐  ┌──────────────┐
          │ ELL ON       │  │ ELL OFF      │
          │ (Discharge)  │  │ (Safe)       │
          └──────────────┘  └──────────────┘
```

**Benefits over standard nodes:**
- Single button to stop entire automation
- Clear visual status
- No coding required
- Integrated with BenchMesh UI for monitoring

## Integration with BenchMesh UI

The main BenchMesh UI will show:
- **Total automations**: Count of all automation nodes
- **Running automations**: Count of currently active automations
- **Individual controls**: Start/stop each automation by name

## API Endpoints

The automation node creates these HTTP endpoints:

### Get all automations status
```bash
GET http://localhost:1880/benchmesh/automations
```

Returns:
```json
{
  "node-id-123": {
    "id": "node-id-123",
    "name": "Overcharge Protection",
    "frequency": 1000,
    "enabled": true,
    "lastTrigger": 1699999999999
  }
}
```

### Control an automation
```bash
POST http://localhost:1880/benchmesh/automations/{node-id}/start
POST http://localhost:1880/benchmesh/automations/{node-id}/stop
POST http://localhost:1880/benchmesh/automations/{node-id}/toggle
```

## Migration from Inject Nodes

If you have existing flows with inject nodes:

**Before:**
```
[Inject: 1s] → [HTTP Request] → [Function] → [Switch] → [HTTP Request]
```

**After:**
```
[Automation: 1s] → [DMM] → [Threshold] → [ELL]
```

**Benefits:**
- Controllable without redeploying
- No function nodes needed
- Clearer visual representation
- Integrated monitoring

## Best Practices

1. **Use Automation nodes instead of Inject nodes** for any recurring tasks
2. **Give automations descriptive names** like "Battery Protection" instead of "Flow 1"
3. **Use Threshold nodes** instead of Switch or Function nodes for comparisons
4. **Use specific instrument nodes** (DMM, PSU, ELL) instead of generic HTTP requests
5. **Test with automation disabled first**, then enable once working

## Troubleshooting

### Nodes don't appear in palette
- Restart Node-RED after installation
- Check Node-RED startup logs for errors
- Verify installation: `cd ~/.node-red && npm list node-red-contrib-benchmesh`

### Automation doesn't start
- Check that API base URL is correct (default: http://localhost:57666)
- Verify BenchMesh backend is running
- Look at node status for error indicators

### Can't control automation from UI
- Ensure Node-RED is accessible at port 1880
- Check browser console for CORS errors
- Verify automation node is deployed (not just configured)

## Development

To modify these nodes:

```bash
cd /home/marek/project/BenchMesh/node-red-contrib-benchmesh
# Edit nodes in nodes/
# Restart Node-RED to test changes
```

## License

MIT

## Support

For issues and questions, see the main BenchMesh repository.
