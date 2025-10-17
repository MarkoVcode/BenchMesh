#!/usr/bin/env python3
"""
Test script for the metrics WebSocket endpoint.
Connects to ws://localhost:57666/ws/metrics and displays real-time metrics.
"""
import asyncio
import websockets
import json
from datetime import datetime

async def monitor_metrics():
    uri = "ws://localhost:57666/ws/metrics"
    print(f"🔌 Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to metrics WebSocket\n")
            print("📊 Monitoring serial port utilization metrics (updates every 30s)...")
            print("=" * 80)

            while True:
                message = await websocket.recv()
                data = json.loads(message)

                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{timestamp}] Received metrics for {len(data)} devices:")
                print("=" * 80)

                if not data:
                    print("  No metrics data available yet.")
                else:
                    for device_id, metrics in data.items():
                        print(f"\n  Device: {device_id}")
                        print(f"    Window Duration: {metrics.get('window_duration_s', 0):.1f}s")
                        print(f"    Utilization:     {metrics.get('utilization_pct', 0):.2f}%")
                        print(f"    QPS:             {metrics.get('qps', 0):.2f}")
                        print(f"    Total Ops:       {metrics.get('total_operations', 0)}")
                        print(f"    API Requests:    {metrics.get('api_request_count', 0)}")

                        api_p95 = metrics.get('api_latency_p95_ms')
                        if api_p95 is not None:
                            print(f"    API Latency P95: {api_p95:.2f}ms")

                        api_p99 = metrics.get('api_latency_p99_ms')
                        if api_p99 is not None:
                            print(f"    API Latency P99: {api_p99:.2f}ms")

                        queue_depth = metrics.get('avg_queue_depth', 0)
                        if queue_depth > 0:
                            print(f"    Avg Queue Depth: {queue_depth:.2f}")

                        poll_duration = metrics.get('avg_poll_duration_ms', 0)
                        if poll_duration > 0:
                            print(f"    Avg Poll Duration: {poll_duration:.2f}ms")

                print("=" * 80)
                print("\nWaiting for next update (30s)... Press Ctrl+C to stop")

    except websockets.exceptions.ConnectionClosed:
        print("\n✗ Connection closed by server")
    except KeyboardInterrupt:
        print("\n\n👋 Stopped monitoring")
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    print("BenchMesh Metrics WebSocket Test\n")
    asyncio.run(monitor_metrics())
