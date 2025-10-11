module.exports = function(RED) {
    function BenchMeshDMMNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        node.deviceId = config.deviceId || 'dmm-1';
        node.channel = config.channel || '1';
        node.operation = config.operation || 'query_measurement';
        node.apiBase = config.apiBase || 'http://localhost:57666';

        node.on('input', function(msg) {
            const deviceId = msg.deviceId || node.deviceId;
            const channel = msg.channel || node.channel;
            const operation = msg.operation || node.operation;

            const url = `${node.apiBase}/instruments/DMM/${deviceId}/${channel}/${operation}`;

            node.status({fill: "blue", shape: "dot", text: "querying..."});

            const http = require('http');
            const urlParsed = new URL(url);

            const options = {
                hostname: urlParsed.hostname,
                port: urlParsed.port,
                path: urlParsed.pathname,
                method: 'GET'
            };

            const req = http.request(options, (res) => {
                let data = '';

                res.on('data', (chunk) => {
                    data += chunk;
                });

                res.on('end', () => {
                    try {
                        const result = JSON.parse(data);
                        msg.payload = result;
                        msg.value = parseFloat(result.value);
                        msg.deviceId = deviceId;
                        msg.channel = channel;

                        node.status({fill: "green", shape: "dot", text: `${msg.value.toFixed(3)}`});
                        node.send(msg);
                    } catch (e) {
                        node.error("Failed to parse response: " + e.message);
                        node.status({fill: "red", shape: "ring", text: "error"});
                    }
                });
            });

            req.on('error', (e) => {
                node.error("Request failed: " + e.message);
                node.status({fill: "red", shape: "ring", text: "error"});
            });

            req.end();
        });
    }

    RED.nodes.registerType("benchmesh-dmm", BenchMeshDMMNode);
}
