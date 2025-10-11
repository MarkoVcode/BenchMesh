module.exports = function(RED) {
    function BenchMeshELLNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        node.deviceId = config.deviceId || 'eol-1';
        node.channel = config.channel || '1';
        node.operation = config.operation || 'set_input';
        node.value = config.value || 'OFF';
        node.apiBase = config.apiBase || 'http://localhost:57666';

        node.on('input', function(msg) {
            const deviceId = msg.deviceId || node.deviceId;
            const channel = msg.channel || node.channel;
            const operation = msg.operation || node.operation;
            const value = msg.value || msg.payload || node.value;

            const url = `${node.apiBase}/instruments/ELL/${deviceId}/${channel}/${operation}/${value}`;

            node.status({fill: "yellow", shape: "dot", text: `setting ${value}...`});

            const http = require('http');
            const urlParsed = new URL(url);

            const options = {
                hostname: urlParsed.hostname,
                port: urlParsed.port,
                path: urlParsed.pathname,
                method: 'POST'
            };

            const req = http.request(options, (res) => {
                let data = '';

                res.on('data', (chunk) => {
                    data += chunk;
                });

                res.on('end', () => {
                    msg.payload = {
                        deviceId: deviceId,
                        channel: channel,
                        operation: operation,
                        value: value,
                        response: data
                    };

                    const statusColor = value === 'ON' ? 'green' : 'grey';
                    node.status({fill: statusColor, shape: "dot", text: value});
                    node.send(msg);
                });
            });

            req.on('error', (e) => {
                node.error("Request failed: " + e.message);
                node.status({fill: "red", shape: "ring", text: "error"});
            });

            req.end();
        });
    }

    RED.nodes.registerType("benchmesh-ell", BenchMeshELLNode);
}
