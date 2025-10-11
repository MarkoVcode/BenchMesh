module.exports = function(RED) {
    function BenchMeshThresholdNode(config) {
        RED.nodes.createNode(this, config);
        const node = this;

        node.threshold = parseFloat(config.threshold) || 0;
        node.comparison = config.comparison || 'gt';
        node.property = config.property || 'value';

        node.on('input', function(msg) {
            const threshold = msg.threshold !== undefined ? parseFloat(msg.threshold) : node.threshold;
            const comparison = msg.comparison || node.comparison;

            // Get the value to compare
            let value;
            if (node.property === 'payload') {
                value = parseFloat(msg.payload);
            } else if (node.property === 'value') {
                value = parseFloat(msg.value);
            } else {
                value = parseFloat(msg[node.property]);
            }

            if (isNaN(value)) {
                node.warn("Value is not a number: " + value);
                return;
            }

            let result = false;
            let statusText = '';

            switch(comparison) {
                case 'gt':
                    result = value > threshold;
                    statusText = `${value.toFixed(3)} > ${threshold}`;
                    break;
                case 'gte':
                    result = value >= threshold;
                    statusText = `${value.toFixed(3)} >= ${threshold}`;
                    break;
                case 'lt':
                    result = value < threshold;
                    statusText = `${value.toFixed(3)} < ${threshold}`;
                    break;
                case 'lte':
                    result = value <= threshold;
                    statusText = `${value.toFixed(3)} <= ${threshold}`;
                    break;
                case 'eq':
                    result = value === threshold;
                    statusText = `${value.toFixed(3)} == ${threshold}`;
                    break;
            }

            msg.thresholdResult = result;
            msg.comparedValue = value;
            msg.thresholdValue = threshold;

            // Output 1 if true, output 2 if false
            if (result) {
                node.status({fill: "green", shape: "dot", text: statusText + " ✓"});
                node.send([msg, null]);
            } else {
                node.status({fill: "grey", shape: "ring", text: statusText + " ✗"});
                node.send([null, msg]);
            }
        });
    }

    RED.nodes.registerType("benchmesh-threshold", BenchMeshThresholdNode);
}
