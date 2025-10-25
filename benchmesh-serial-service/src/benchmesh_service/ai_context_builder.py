"""
AI Context Builder for generating comprehensive system prompts and context.

This module builds dynamic context about the BenchMesh system, configured instruments,
available APIs, and Node-RED integration for AI assistants to understand and operate
the lab instrument control system.
"""

import json
from typing import Any, Dict, List, Optional
from .serial_manager import SerialManager, _load_manifest
from .manifest_resolver import ManifestResolver
from .method_inspector import inspect_driver_methods


class AIContextBuilder:
    """
    Builds comprehensive AI assistant context from current system state.

    Aggregates information from:
    - SerialManager (configured devices, connections)
    - ManifestResolver (driver capabilities)
    - Method inspection (available operations)
    - Documentation (guides and patterns)
    """

    def __init__(
        self,
        manager: Optional[SerialManager] = None,
        manifest_resolver: Optional[ManifestResolver] = None,
        version: str = "0.1.0"
    ):
        self.manager = manager
        self.manifest_resolver = manifest_resolver
        self.version = version

    async def build(
        self,
        sections: List[str] = None,
        format: str = "markdown"
    ) -> str | Dict:
        """
        Build complete AI context.

        Args:
            sections: List of sections to include (default: all)
            format: Output format ("markdown" or "json")

        Returns:
            Formatted context as markdown string or JSON dict
        """
        if sections is None:
            sections = ["system", "config", "instruments", "api", "nodered", "safety", "examples"]

        data = {}

        if "system" in sections:
            data["system"] = self.build_system_overview()

        if "config" in sections or "instruments" in sections:
            data["instruments"] = await self.build_instruments_section()

        if "api" in sections:
            data["api_patterns"] = self.build_api_patterns()

        if "nodered" in sections:
            data["nodered"] = self.build_nodered_integration()

        if "safety" in sections:
            data["safety"] = self.build_safety_rules()

        if "examples" in sections:
            data["examples"] = self.build_common_tasks()

        if format == "markdown":
            return self.format_as_markdown(data)
        else:
            return data

    def build_system_overview(self) -> Dict[str, Any]:
        """Build system overview section."""
        return {
            "name": "BenchMesh",
            "version": self.version,
            "description": "Lab Instrument Control System for serial-connected instruments",
            "components": ["FastAPI Backend", "React Frontend", "Node-RED Automation"],
            "architecture": {
                "backend": "Python FastAPI on port 57666",
                "frontend": "React + TypeScript UI on /ui",
                "automation": "Node-RED on port 1880",
                "protocols": ["REST API", "WebSocket", "Serial (RS-232)"]
            },
            "purpose": "Unified control of lab instruments (PSU, DMM, ELL, etc.) with automation capabilities"
        }

    async def build_instruments_section(self) -> List[Dict[str, Any]]:
        """Build instruments section with current configuration and capabilities."""
        instruments = []

        if not self.manager:
            return instruments

        registry = getattr(self.manager, 'registry', {}) or {}

        for dev in self.manager.devices:
            dev_id = dev.get('id')
            if not dev_id:
                continue

            # Get device connection and health
            conn = self.manager.dev_conns.get(dev_id)
            drv = self.manager.connections.get(dev_id)

            reg_data = registry.get(dev_id, {})
            idn = reg_data.get('IDN', '')

            # Determine status
            is_online = bool(conn and conn.is_alive() and idn and str(idn).strip())

            instrument = {
                "id": dev_id,
                "name": dev.get('name', dev_id),
                "driver": dev.get('driver'),
                "port": dev.get('port'),
                "model": dev.get('model'),
                "status": "online" if is_online else "offline",
                "idn": idn if idn else None
            }

            # Get instrument classes and methods
            if self.manifest_resolver and drv:
                try:
                    driver_key = dev.get('driver')
                    manifest = _load_manifest(driver_key) if driver_key else None

                    if isinstance(manifest, dict):
                        model_cfg = self.manifest_resolver._get_model_cfg(manifest, dev)

                        if isinstance(model_cfg, dict):
                            inst_class_block = model_cfg.get('instrument_class', {})

                            # Get classes
                            classes = []
                            for klass, klass_cfg in inst_class_block.items():
                                if len(klass) == 3 and klass.isupper():
                                    features = klass_cfg.get('features', {})
                                    channels = int(features.get('channels', 1) or 1)
                                    classes.append({
                                        "class": klass,
                                        "channels": channels
                                    })

                            instrument["classes"] = classes

                            # Get available methods
                            manifest_methods = model_cfg.get('methods', {})
                            methods = inspect_driver_methods(drv, manifest_methods)

                            # Organize methods by type
                            query_methods = [m for m in methods if m['http_method'] == 'GET']
                            set_methods = [m for m in methods if m['http_method'] == 'POST']

                            instrument["methods"] = {
                                "query": query_methods,
                                "set": set_methods
                            }
                except Exception:
                    pass  # Gracefully handle errors

            instruments.append(instrument)

        return instruments

    def build_api_patterns(self) -> Dict[str, Any]:
        """Build API usage patterns section."""
        return {
            "base_url": "http://localhost:57666",
            "patterns": {
                "read_measurement": {
                    "method": "GET",
                    "pattern": "/instruments/{CLASS}/{DEVICE_ID}/{CHANNEL}/{METHOD}",
                    "description": "Query instrument measurements or status",
                    "example": "GET /instruments/DMM/dmm-1/1/measurement"
                },
                "set_value": {
                    "method": "POST",
                    "pattern": "/instruments/{CLASS}/{DEVICE_ID}/{CHANNEL}/{METHOD}/{VALUE}",
                    "description": "Control instrument settings",
                    "example": "POST /instruments/PSU/psu-1/1/voltage/5.0"
                },
                "list_instruments": {
                    "method": "GET",
                    "pattern": "/instruments",
                    "description": "Get all configured instruments"
                },
                "get_config": {
                    "method": "GET",
                    "pattern": "/config",
                    "description": "Get current configuration"
                },
                "discover_methods": {
                    "method": "GET",
                    "pattern": "/instruments/{CLASS}/{DEVICE_ID}/methods",
                    "description": "Discover available methods for a device"
                }
            },
            "websocket": {
                "registry": "ws://localhost:57666/ws/registry",
                "description": "Real-time device status updates",
                "update_rate": "~200ms"
            }
        }

    def build_nodered_integration(self) -> Dict[str, Any]:
        """Build Node-RED integration section."""
        return {
            "base_url": "http://localhost:1880",
            "editor_url": "http://localhost:1880",
            "ui_url": "http://localhost:1880/ui",
            "custom_nodes": [
                {
                    "type": "benchmesh-automation",
                    "description": "Controllable automation trigger with start/stop capabilities",
                    "use_case": "Replace inject nodes for recurring tasks that need runtime control",
                    "features": ["Start/stop button", "Enable/disable", "Visual status", "HTTP API control"]
                },
                {
                    "type": "benchmesh-psu",
                    "description": "Power supply control and monitoring",
                    "use_case": "Query voltage/current, set values, control output state"
                },
                {
                    "type": "benchmesh-dmm",
                    "description": "Digital multimeter reading",
                    "use_case": "Read voltage, current, resistance measurements",
                    "features": ["Auto-parse values", "Display current reading"]
                },
                {
                    "type": "benchmesh-ell",
                    "description": "Electronic load control",
                    "use_case": "Set mode (CC/CV/CP/CR), control load on/off"
                },
                {
                    "type": "benchmesh-threshold",
                    "description": "Threshold comparison for safety checks",
                    "use_case": "Compare values against limits, visual pass/fail",
                    "features": ["Two outputs (above/below)", "Visual indication"]
                },
                {
                    "type": "benchmesh-instrument",
                    "description": "Generic instrument API call",
                    "use_case": "Use when specific node doesn't exist or for custom operations"
                }
            ],
            "automation_api": {
                "list": "GET http://localhost:1880/benchmesh/automations",
                "start": "POST http://localhost:1880/benchmesh/automations/{node-id}/start",
                "stop": "POST http://localhost:1880/benchmesh/automations/{node-id}/stop",
                "toggle": "POST http://localhost:1880/benchmesh/automations/{node-id}/toggle"
            },
            "common_patterns": [
                {
                    "name": "Periodic Monitoring",
                    "flow": "[Automation: 1s] → [DMM Read] → [Debug/Process]",
                    "description": "Monitor measurements at regular intervals"
                },
                {
                    "name": "Threshold Protection",
                    "flow": "[Automation] → [DMM] → [Threshold] → [ELL Control]",
                    "description": "Safety cutoff when measurement exceeds limit"
                },
                {
                    "name": "Sequential Control",
                    "flow": "[Automation] → [PSU Set] → [Delay] → [DMM Read] → [Log]",
                    "description": "Set value, wait for settling, measure, record"
                }
            ]
        }

    def build_safety_rules(self) -> List[str]:
        """Build safety guidelines section."""
        return [
            "Always verify PSU output is OFF before changing voltage settings",
            "Set current limit BEFORE enabling PSU output to prevent damage",
            "Do not exceed device maximum ratings (check driver manifest)",
            "Use gradual voltage ramps for inductive loads to prevent spikes",
            "Implement overcharge/overcurrent protection in automations",
            "Monitor device health status before critical operations",
            "Add delays after set operations to allow settling time",
            "Use try-catch patterns in automations for error handling",
            "Test flows with automation disabled before enabling",
            "Verify connections before starting automated sequences",
            "Include timeout mechanisms in long-running automations",
            "Log all critical operations for troubleshooting"
        ]

    def build_common_tasks(self) -> List[Dict[str, Any]]:
        """Build common task examples."""
        tasks = []

        # Find PSU and DMM if available
        psu = None
        dmm = None

        if self.manager:
            for dev in self.manager.devices:
                driver = dev.get('driver', '')
                if 'psu' in driver.lower() or 'spm' in driver.lower() or 'tenma' in driver.lower():
                    psu = dev
                elif 'dmm' in driver.lower() or 'xdm' in driver.lower():
                    dmm = dev

        # PSU tasks
        if psu:
            psu_id = psu.get('id')
            psu_name = psu.get('name', psu_id)

            tasks.append({
                "task": f"Set {psu_name} voltage to 5V and enable output",
                "steps": [
                    f"1. Set voltage: POST /instruments/PSU/{psu_id}/1/voltage/5.0",
                    f"2. Enable output: POST /instruments/PSU/{psu_id}/1/output/true",
                    f"3. Verify: GET /instruments/PSU/{psu_id}/1/output_voltage"
                ],
                "curl_example": f"""
# Set voltage
curl -X POST http://localhost:57666/instruments/PSU/{psu_id}/1/voltage/5.0

# Enable output
curl -X POST http://localhost:57666/instruments/PSU/{psu_id}/1/output/true

# Verify
curl http://localhost:57666/instruments/PSU/{psu_id}/1/output_voltage
""".strip()
            })

            tasks.append({
                "task": f"Ramp {psu_name} from 0V to 5V in 1V steps",
                "python_example": f"""
import requests, time

base = "http://localhost:57666"
for voltage in [0, 1, 2, 3, 4, 5]:
    # Set voltage
    requests.post(f"{{base}}/instruments/PSU/{psu_id}/1/voltage/{{voltage}}")
    time.sleep(0.5)  # Wait for settling

    # Read back
    resp = requests.get(f"{{base}}/instruments/PSU/{psu_id}/1/output_voltage")
    actual = resp.json()['value']
    print(f"Set: {{voltage}}V, Actual: {{actual}}")
""".strip()
            })

        # DMM tasks
        if dmm:
            dmm_id = dmm.get('id')
            dmm_name = dmm.get('name', dmm_id)

            tasks.append({
                "task": f"Read {dmm_name} measurement",
                "steps": [
                    f"GET /instruments/DMM/{dmm_id}/1/measurement"
                ],
                "curl_example": f"curl http://localhost:57666/instruments/DMM/{dmm_id}/1/measurement"
            })

        # Combined tasks
        if psu and dmm:
            tasks.append({
                "task": "Set PSU and monitor with DMM",
                "node_red_flow": {
                    "description": "Complete automation flow",
                    "nodes": [
                        {"type": "benchmesh-automation", "name": "Control Loop", "frequency": 1000},
                        {"type": "benchmesh-psu", "device": psu.get('id'), "operation": "set_voltage", "value": 3.3},
                        {"type": "delay", "timeout": 500},
                        {"type": "benchmesh-dmm", "device": dmm.get('id'), "channel": 1},
                        {"type": "debug", "name": "Log Measurement"}
                    ]
                }
            })

        return tasks

    def format_as_markdown(self, data: Dict[str, Any]) -> str:
        """
        Format context data as markdown for LLM system prompt.

        Args:
            data: Context data dictionary

        Returns:
            Formatted markdown string
        """
        md = []

        md.append("# BenchMesh Lab Instrument Control System - AI Assistant Context\n")
        md.append("## System Overview\n")

        if "system" in data:
            sys = data["system"]
            md.append(f"You are an AI assistant operating **{sys['name']} v{sys['version']}**, {sys['description']}.\n")
            md.append(f"**Purpose**: {sys['purpose']}\n")
            md.append(f"\n**System Components**:\n")
            for comp in sys['components']:
                md.append(f"- {comp}\n")
            md.append("\n")

        if "instruments" in data and data["instruments"]:
            md.append("## Currently Configured Instruments\n")

            for idx, inst in enumerate(data["instruments"], 1):
                status_emoji = "🟢" if inst['status'] == 'online' else "🔴"
                md.append(f"\n### {idx}. {inst['name']} ({inst['id']}) {status_emoji}\n")
                md.append(f"- **Type**: {', '.join([c['class'] for c in inst.get('classes', [])]) or 'Unknown'}\n")
                md.append(f"- **Driver**: {inst['driver']}\n")
                md.append(f"- **Port**: {inst['port']}\n")
                if inst.get('model'):
                    md.append(f"- **Model**: {inst['model']}\n")
                if inst.get('classes'):
                    for cls in inst['classes']:
                        md.append(f"- **Channels**: {cls['channels']}\n")
                md.append(f"- **Status**: {inst['status'].upper()}\n")

                if inst.get('idn'):
                    md.append(f"- **IDN**: {inst['idn']}\n")

                # Add methods
                methods = inst.get('methods', {})
                query_methods = methods.get('query', [])
                set_methods = methods.get('set', [])

                if query_methods or set_methods:
                    md.append(f"\n**Available Operations**:\n")

                    if query_methods:
                        md.append("\n*Query Operations (Read)*:\n")
                        for method in query_methods[:5]:  # Limit to first 5
                            klass = inst.get('classes', [{}])[0].get('class', 'INST')
                            example_url = f"/instruments/{klass}/{inst['id']}/1/{method['name']}"
                            md.append(f"- `GET {example_url}` - {method['description']}\n")

                    if set_methods:
                        md.append("\n*Control Operations (Write)*:\n")
                        for method in set_methods[:5]:  # Limit to first 5
                            klass = inst.get('classes', [{}])[0].get('class', 'INST')
                            params = method.get('parameters', [])
                            param_example = "/{value}" if params else ""
                            example_url = f"/instruments/{klass}/{inst['id']}/1/{method['name']}{param_example}"
                            md.append(f"- `POST {example_url}` - {method['description']}\n")

        if "api_patterns" in data:
            md.append("\n## API Patterns\n")
            api = data["api_patterns"]
            md.append(f"\n**Base URL**: `{api['base_url']}`\n")

            md.append("\n### Common Endpoints\n")
            for name, pattern_info in api['patterns'].items():
                md.append(f"\n**{pattern_info['description']}**:\n")
                md.append(f"```\n{pattern_info['method']} {pattern_info['pattern']}\n```\n")
                if 'example' in pattern_info:
                    md.append(f"Example: `{pattern_info['example']}`\n")

            if 'websocket' in api:
                ws = api['websocket']
                md.append(f"\n### Real-Time Updates\n")
                md.append(f"**WebSocket**: `{ws['registry']}`\n")
                md.append(f"- {ws['description']}\n")
                md.append(f"- Update rate: {ws['update_rate']}\n")

        if "nodered" in data:
            md.append("\n## Node-RED Automation\n")
            nr = data["nodered"]
            md.append(f"\n**Node-RED Editor**: {nr['editor_url']}\n")

            md.append("\n### Available Custom Nodes\n")
            for node in nr['custom_nodes']:
                md.append(f"\n**{node['type']}**:\n")
                md.append(f"- {node['description']}\n")
                md.append(f"- Use case: {node['use_case']}\n")
                if 'features' in node:
                    md.append(f"- Features: {', '.join(node['features'])}\n")

            md.append("\n### Common Flow Patterns\n")
            for pattern in nr.get('common_patterns', []):
                md.append(f"\n**{pattern['name']}**:\n")
                md.append(f"```\n{pattern['flow']}\n```\n")
                md.append(f"{pattern['description']}\n")

            md.append("\n### Automation Control API\n")
            auto_api = nr.get('automation_api', {})
            for action, endpoint in auto_api.items():
                md.append(f"- {action.capitalize()}: `{endpoint}`\n")

        if "safety" in data:
            md.append("\n## ⚠️ Safety Guidelines\n")
            md.append("\n**IMPORTANT**: Follow these safety rules when operating instruments:\n")
            for rule in data["safety"]:
                md.append(f"- {rule}\n")

        if "examples" in data and data["examples"]:
            md.append("\n## Common Tasks & Examples\n")

            for task in data["examples"]:
                md.append(f"\n### Task: {task['task']}\n")

                if 'steps' in task:
                    md.append("\n**Steps**:\n")
                    for step in task['steps']:
                        md.append(f"{step}\n")

                if 'curl_example' in task:
                    md.append("\n**Example (curl)**:\n")
                    md.append(f"```bash\n{task['curl_example']}\n```\n")

                if 'python_example' in task:
                    md.append("\n**Example (Python)**:\n")
                    md.append(f"```python\n{task['python_example']}\n```\n")

                if 'node_red_flow' in task:
                    flow = task['node_red_flow']
                    md.append(f"\n**Node-RED Flow** ({flow['description']}):\n")
                    md.append("```json\n")
                    md.append(json.dumps(flow['nodes'], indent=2))
                    md.append("\n```\n")

        md.append("\n## How to Help Users\n")
        md.append("""
When a user asks you to operate instruments or create automations:

1. **Understand Intent**: Identify what the user wants to achieve
2. **Match Devices**: Find the appropriate configured instruments
3. **Plan Operations**: Determine the sequence of API calls needed
4. **Check Safety**: Verify operations are safe (voltage limits, output state, etc.)
5. **Execute**: Make API calls in the correct order
6. **Verify**: Read back status to confirm success
7. **Explain**: Clearly describe what was done and current state

**Example Dialog**:
```
User: "Set the power supply to 3.3V and turn it on"

You should:
1. Identify the PSU from configured instruments
2. Plan: set voltage → enable output → verify
3. Execute API calls
4. Respond: "PSU '{name}' is now outputting 3.30V at channel 1"
```

For Node-RED automation requests:
1. Understand the automation goal
2. Design the flow using appropriate BenchMesh nodes
3. Provide flow JSON or step-by-step setup instructions
4. Explain how to import and deploy the flow
""")

        return "".join(md)
