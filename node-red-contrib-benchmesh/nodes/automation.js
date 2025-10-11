// Module-level storage for automations (shared across all instances and API)
let globalAutomations = {};

module.exports = function(RED) {
    function BenchMeshAutomationNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        node.automationName = config.automationName || 'Unnamed Automation';
        node.frequency = parseInt(config.frequency) || 1000;
        node.enabled = config.enabled !== false; // Default to true
        node.interval = null;

        const startAutomation = () => {
            if (node.interval) {
                clearInterval(node.interval);
            }

            node.enabled = true;
            node.status({fill: "green", shape: "dot", text: `running (${node.frequency}ms)`});

            // Update global tracking
            globalAutomations[node.id] = {
                id: node.id,
                name: node.automationName,
                frequency: node.frequency,
                enabled: true,
                lastTrigger: Date.now()
            };

            node.interval = setInterval(() => {
                globalAutomations[node.id].lastTrigger = Date.now();

                node.send({
                    payload: Date.now(),
                    automationId: node.id,
                    automationName: node.automationName
                });
            }, node.frequency);
        };

        const stopAutomation = () => {
            if (node.interval) {
                clearInterval(node.interval);
                node.interval = null;
            }

            node.enabled = false;
            node.status({fill: "red", shape: "ring", text: "stopped"});

            // Update global tracking
            if (globalAutomations[node.id]) {
                globalAutomations[node.id].enabled = false;
            }
        };

        // Handle input messages for control
        node.on('input', function(msg) {
            const command = msg.payload;

            if (command === 'start' || command === 'START' || command === true) {
                startAutomation();
            } else if (command === 'stop' || command === 'STOP' || command === false) {
                stopAutomation();
            } else if (command === 'toggle' || command === 'TOGGLE') {
                if (node.enabled) {
                    stopAutomation();
                } else {
                    startAutomation();
                }
            }
        });

        // Start if enabled by default
        if (node.enabled) {
            startAutomation();
        } else {
            node.status({fill: "red", shape: "ring", text: "stopped"});
            // Register as stopped
            globalAutomations[node.id] = {
                id: node.id,
                name: node.automationName,
                frequency: node.frequency,
                enabled: false
            };
        }

        node.on('close', function() {
            stopAutomation();
            // Remove from global tracking
            delete globalAutomations[node.id];
        });
    }

    RED.nodes.registerType("benchmesh-automation", BenchMeshAutomationNode);

    // API endpoint to get automation status
    RED.httpAdmin.get('/benchmesh/automations', function(req, res) {
        res.json(globalAutomations);
    });

    // API endpoint to control automations
    RED.httpAdmin.post('/benchmesh/automations/:id/:action', function(req, res) {
        const { id, action } = req.params;

        // Find the node and send it a command
        const targetNode = RED.nodes.getNode(id);
        if (targetNode) {
            targetNode.receive({ payload: action });
            res.json({ success: true, id, action });
        } else {
            res.status(404).json({ success: false, error: 'Automation not found' });
        }
    });
}
