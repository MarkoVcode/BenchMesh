# Automation & Node-RED

BenchMesh integrates with Node-RED to provide powerful automation capabilities for your lab instruments.

## What is Node-RED?

Node-RED is a visual programming tool for wiring together hardware devices, APIs, and online services. With BenchMesh, you can:

- Create automated test sequences
- Log measurements to databases or files
- Build complex workflows with conditional logic
- Integrate with other lab systems
- Schedule periodic measurements

## Accessing Node-RED

Node-RED runs on port 1880 when started via `./start.sh`:

**URL**: http://localhost:1880

## BenchMesh Custom Nodes

BenchMesh provides custom Node-RED nodes for instrument control:

### Available Nodes

1. **benchmesh-status** - Get device status and measurements
2. **benchmesh-call** - Call device methods (control instruments)
3. **benchmesh-instruments** - List all configured instruments

## Installing Custom Nodes

BenchMesh nodes are automatically available when starting via `./start.sh`.

To install manually in an existing Node-RED instance:

```bash
cd ~/.node-red
npm install /path/to/BenchMesh/benchmesh-nodered-nodes
```

Restart Node-RED after installation.

## Using BenchMesh Nodes

### Getting Device Status

The **benchmesh-status** node retrieves current device measurements:

1. Drag **benchmesh-status** node to the flow
2. Double-click to configure:
   - **Device ID**: Enter device ID from config (e.g., `psu-1`)
   - **API Base**: Usually `http://localhost:57666`
3. Connect to a debug or processing node
4. Deploy the flow

**Output**: Device status object with current measurements

Example output for PSU:
```json
{
  "voltage": 5.00,
  "current": 0.15,
  "output": true
}
```

### Calling Device Methods

The **benchmesh-call** node executes device control commands:

1. Drag **benchmesh-call** node to the flow
2. Double-click to configure:
   - **Device ID**: Target device
   - **Method**: Method name (e.g., `set_voltage`)
   - **Arguments**: JSON array of arguments
   - **API Base**: `http://localhost:57666`

Example configurations:

**Set PSU voltage to 5V:**
- Device ID: `psu-1`
- Method: `set_voltage`
- Arguments: `[5.0]`

**Set PSU output ON:**
- Device ID: `psu-1`
- Method: `set_output`
- Arguments: `[true]`

**Set voltage with channel:**
- Device ID: `psu-dual`
- Method: `set_voltage`
- Arguments: `[5.0, {"ch": 1}]`

### Listing Instruments

The **benchmesh-instruments** node returns all configured devices:

1. Drag **benchmesh-instruments** node to the flow
2. Configure API base if needed
3. Connect to processing nodes
4. Deploy

**Output**: Array of instrument objects with ID, name, driver, and class information

## Example Flows

### Example 1: Periodic Voltage Monitoring

Monitor PSU voltage every 5 seconds and send alerts if out of range:

```
[inject (5s)] → [benchmesh-status] → [function: check range] → [debug/alert]
```

1. **Inject node**: Set to repeat every 5 seconds
2. **benchmesh-status**: Device ID = `psu-1`
3. **Function node**:
   ```javascript
   const voltage = msg.payload.voltage;
   if (voltage < 4.9 || voltage > 5.1) {
       msg.payload = `Voltage out of range: ${voltage}V`;
       return msg;
   }
   return null;
   ```
4. **Debug node**: Display alerts

### Example 2: Automated Test Sequence

Ramp PSU voltage and log current measurements:

```
[inject] → [function: ramp] → [benchmesh-call] → [delay 100ms] → [benchmesh-status] → [csv]
```

1. **Inject node**: Manual trigger
2. **Function node** (ramp generator):
   ```javascript
   const voltages = [0, 1, 2, 3, 4, 5];
   const messages = voltages.map(v => ({
       payload: {
           device_id: "psu-1",
           method: "set_voltage",
           args: [v]
       }
   }));
   return [messages];
   ```
3. **benchmesh-call**: Set voltage
4. **Delay**: Wait for settling
5. **benchmesh-status**: Read current
6. **CSV node**: Log to file

### Example 3: Multi-Device Coordination

Control PSU and monitor with DMM simultaneously:

```
[inject] → [benchmesh-call: PSU] → [delay] → [benchmesh-status: DMM] → [function: log]
```

1. Set PSU voltage
2. Wait for settling time
3. Read DMM measurement
4. Log correlated data

## Working with Node-RED

### Creating a New Flow

1. Open Node-RED: http://localhost:1880
2. Drag nodes from the left palette
3. Wire nodes together by connecting output to input
4. Double-click nodes to configure
5. Click **Deploy** to activate

### Debugging Flows

1. Add **debug** nodes to outputs
2. View output in the right sidebar (bug icon)
3. Use **catch** nodes for error handling
4. Enable node status messages

### Importing/Exporting Flows

**Export:**
1. Select nodes (or Ctrl+A for all)
2. Menu → Export → Clipboard
3. Save JSON to file

**Import:**
1. Menu → Import → Clipboard
2. Paste JSON
3. Click Import

### Node-RED Resources

- **User Guide**: https://nodered.org/docs/user-guide/
- **Node Catalog**: https://flows.nodered.org/
- **Tutorials**: https://nodered.org/docs/tutorials/

## API-Based Automation

You can also automate without Node-RED using the REST API directly.

### Example: Python Script

```python
import requests
import time

API_BASE = "http://localhost:57666"

# Set PSU voltage
requests.post(f"{API_BASE}/api/call", json={
    "device_id": "psu-1",
    "method": "set_voltage",
    "args": [5.0]
})

# Wait for settling
time.sleep(0.5)

# Read status
response = requests.get(f"{API_BASE}/instruments")
instruments = response.json()
psu = next(i for i in instruments if i["id"] == "psu-1")
print(f"Voltage: {psu['status']['voltage']}V")
```

### Example: Bash Script

```bash
API_BASE="http://localhost:57666"

# Set voltage to 3.3V
curl -X POST "$API_BASE/api/call" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"psu-1","method":"set_voltage","args":[3.3]}'

# Get status
curl "$API_BASE/instruments" | jq '.[] | select(.id=="psu-1") | .status'
```

## Best Practices

1. **Error Handling**: Always add catch nodes for error handling
2. **Rate Limiting**: Don't poll too frequently (max 1-2 Hz recommended)
3. **Logging**: Use file or database nodes for persistent logs
4. **Testing**: Test flows with single inject before automation
5. **Documentation**: Add comment nodes to document complex flows
6. **Backups**: Export flows regularly

## Troubleshooting

### BenchMesh Nodes Not Appearing

- Restart Node-RED after installation
- Check `~/.node-red/package.json` includes benchmesh nodes
- View Node-RED startup logs for errors

### API Connection Failed

- Verify BenchMesh backend is running (http://localhost:57666/docs)
- Check API base URL in node configuration
- Ensure firewall allows local connections

### Method Call Errors

- Verify device ID matches configuration
- Check method name spelling (case-sensitive)
- Ensure arguments match method signature
- View debug output for error messages

## Advanced Topics

### Custom Dashboard

Create a Node-RED dashboard for monitoring:

1. Install dashboard: `npm install node-red-dashboard`
2. Use dashboard nodes (gauge, chart, button)
3. Access at http://localhost:1880/ui

### MQTT Integration

Publish measurements to MQTT:

1. Install MQTT nodes
2. Configure MQTT broker
3. Publish device status to topics

### Database Logging

Store measurements in database:

1. Install database nodes (MySQL, PostgreSQL, InfluxDB)
2. Create logging flow
3. Query historical data
