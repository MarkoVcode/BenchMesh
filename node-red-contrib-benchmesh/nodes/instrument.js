// Generic instrument node - use when specific node doesn't exist
module.exports = function(RED) {
    function BenchMeshInstrumentNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        node.apiBase = config.apiBase || 'http://localhost:57666';

        node.on('input', function(msg) {
            // Expect msg.path like "/instruments/DMM/dmm-1/1/query_measurement"
            const path = msg.path || config.path;
            const method = msg.method || config.method || 'GET';

            if (!path) {
                node.error("No path specified");
                return;
            }

            const url = node.apiBase + path;
            node.status({fill: "blue", shape: "dot", text: "requesting..."});

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
                        msg.payload = JSON.parse(data);
                    } catch (e) {
                        msg.payload = data;
                    }
                    node.status({fill: "green", shape: "dot", text: "ok"});
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

    RED.nodes.registerType("benchmesh-instrument", BenchMeshInstrumentNode);
}
