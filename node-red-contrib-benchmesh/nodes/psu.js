module.exports = function(RED) {
    function BenchMeshPSUNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        node.deviceId = config.deviceId || 'psu-1';
        node.channel = config.channel || '1';
        node.operation = config.operation || 'query_voltage';
        node.value = config.value || '';
        node.apiBase = config.apiBase || 'http://localhost:57666';

        node.on('input', function(msg) {
            const deviceId = msg.deviceId || node.deviceId;
            const channel = msg.channel || node.channel;
            const operation = msg.operation || node.operation;
            const value = msg.value || node.value;

            let url = `${node.apiBase}/instruments/PSU/${deviceId}/${channel}/${operation}`;
            if (value) {
                url += `/${value}`;
            }

            const method = operation.startsWith('set_') ? 'POST' : 'GET';
            node.status({fill: "blue", shape: "dot", text: operation});

            const http = require('http');
            const urlParsed = new URL(url);

            const options = {
                hostname: urlParsed.hostname,
                port: urlParsed.port,
                path: urlParsed.pathname,
                method: method
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
                        if (result.value !== undefined) {
                            msg.value = parseFloat(result.value);
                            node.status({fill: "green", shape: "dot", text: `${msg.value.toFixed(3)}`});
                        } else {
                            node.status({fill: "green", shape: "dot", text: "ok"});
                        }
                        node.send(msg);
                    } catch (e) {
                        msg.payload = data;
                        node.status({fill: "green", shape: "dot", text: "ok"});
                        node.send(msg);
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

    RED.nodes.registerType("benchmesh-psu", BenchMeshPSUNode);
}
