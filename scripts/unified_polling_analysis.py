#!/usr/bin/env python3
"""
BenchMesh Unified Polling Analysis

Analyzes the impact of unified parallel polling on API responsiveness,
modeling different utilization levels and prioritization strategies.

This script answers the key question:
"If we poll all devices aggressively in parallel, how do we prevent API blocking?"
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


@dataclass
class DeviceProfile:
    """Profile for a single device's polling characteristics"""
    device_id: str
    num_channels: int = 1
    query_time_ms: float = 8.7  # Time per single query

    @property
    def poll_duration_ms(self) -> float:
        """Total time to poll all channels sequentially"""
        return self.num_channels * self.query_time_ms


@dataclass
class PollingConfig:
    """Configuration for unified polling"""
    poll_interval_ms: float = 500.0  # How often to poll all devices
    devices: List[DeviceProfile] = None

    def __post_init__(self):
        if self.devices is None:
            self.devices = []

    @property
    def total_poll_duration_ms(self) -> float:
        """Time for ALL devices to complete polling (in parallel)"""
        # In parallel, total time = max of all device times
        if not self.devices:
            return 0.0
        return max(d.poll_duration_ms for d in self.devices)

    @property
    def utilization_pct(self) -> float:
        """What % of time is spent polling (in parallel)"""
        return (self.total_poll_duration_ms / self.poll_interval_ms) * 100

    @property
    def idle_pct(self) -> float:
        """What % of time is idle between polls"""
        return 100 - self.utilization_pct


class RequestPriority(Enum):
    """Priority levels for device requests"""
    LOW = 1      # Background polling
    NORMAL = 5   # Regular operations
    HIGH = 10    # User-triggered API calls
    URGENT = 20  # Critical operations


@dataclass
class ApiLatencyModel:
    """Models API request latency under different polling scenarios"""
    config: PollingConfig

    def calculate_latency_no_priority(self, device: DeviceProfile) -> Dict:
        """Calculate API latency WITHOUT priority queue (current implementation)"""
        api_query_ms = device.query_time_ms

        # Best case: no polling in progress
        best_case_ms = api_query_ms

        # Worst case: API arrives just as polling starts
        # Must wait for full poll cycle before API gets lock
        worst_case_ms = device.poll_duration_ms + api_query_ms

        # Average case: uniform random arrival during poll cycle
        avg_wait_ms = device.poll_duration_ms / 2
        average_case_ms = avg_wait_ms + api_query_ms

        # Probability of API request arriving during poll
        # = poll_duration / poll_interval
        blocking_probability = device.poll_duration_ms / self.config.poll_interval_ms

        return {
            "device_id": device.device_id,
            "best_case_ms": best_case_ms,
            "average_case_ms": average_case_ms,
            "worst_case_ms": worst_case_ms,
            "blocking_probability": blocking_probability,
            "expected_wait_ms": avg_wait_ms * blocking_probability,
        }

    def calculate_latency_with_priority(self, device: DeviceProfile,
                                       preemptive: bool = False) -> Dict:
        """Calculate API latency WITH priority queue"""
        api_query_ms = device.query_time_ms

        if preemptive:
            # Preemptive: API can interrupt polling
            # Best case: no polling in progress
            best_case_ms = api_query_ms

            # Worst case: Currently executing one poll query, must finish it
            # Then API runs immediately
            worst_case_ms = device.query_time_ms + api_query_ms

            # Average case: API arrives during random query in poll cycle
            # Must wait for current query to finish (not entire poll)
            avg_wait_ms = device.query_time_ms / 2
            average_case_ms = avg_wait_ms + api_query_ms

            blocking_probability = device.poll_duration_ms / self.config.poll_interval_ms

            return {
                "device_id": device.device_id,
                "mode": "PREEMPTIVE",
                "best_case_ms": best_case_ms,
                "average_case_ms": average_case_ms,
                "worst_case_ms": worst_case_ms,
                "blocking_probability": blocking_probability,
                "expected_wait_ms": avg_wait_ms * blocking_probability,
            }
        else:
            # Non-preemptive: API goes to front of queue but waits for current operation
            # Best case: no polling in progress
            best_case_ms = api_query_ms

            # Worst case: Full poll cycle in progress, but no more polling after
            # (unlike no-priority where another poll might start)
            worst_case_ms = device.poll_duration_ms + api_query_ms

            # Average case: Same as no priority, but no subsequent polls can block
            avg_wait_ms = device.poll_duration_ms / 2
            average_case_ms = avg_wait_ms + api_query_ms

            blocking_probability = device.poll_duration_ms / self.config.poll_interval_ms

            return {
                "device_id": device.device_id,
                "mode": "NON-PREEMPTIVE PRIORITY",
                "best_case_ms": best_case_ms,
                "average_case_ms": average_case_ms,
                "worst_case_ms": worst_case_ms,
                "blocking_probability": blocking_probability,
                "expected_wait_ms": avg_wait_ms * blocking_probability,
            }

    def calculate_max_safe_utilization(self, max_acceptable_latency_ms: float = 50.0) -> Dict:
        """Calculate maximum safe polling utilization to keep API latency acceptable"""
        # For worst case, we need: poll_duration + api_query <= max_acceptable_latency
        # This gives us: poll_duration <= max_acceptable_latency - api_query

        results = []
        for device in self.config.devices:
            api_query_ms = device.query_time_ms
            max_poll_duration_ms = max_acceptable_latency_ms - api_query_ms

            # What utilization does this imply?
            # utilization = poll_duration / poll_interval
            # We want: device.poll_duration / poll_interval <= max_safe_utilization
            max_safe_utilization_pct = (max_poll_duration_ms / self.config.poll_interval_ms) * 100

            # Current utilization for this device
            current_utilization_pct = (device.poll_duration_ms / self.config.poll_interval_ms) * 100

            results.append({
                "device_id": device.device_id,
                "current_poll_duration_ms": device.poll_duration_ms,
                "max_safe_poll_duration_ms": max_poll_duration_ms,
                "current_utilization_pct": current_utilization_pct,
                "max_safe_utilization_pct": max_safe_utilization_pct,
                "is_safe": current_utilization_pct <= max_safe_utilization_pct,
                "headroom_pct": max_safe_utilization_pct - current_utilization_pct,
            })

        return {
            "max_acceptable_latency_ms": max_acceptable_latency_ms,
            "poll_interval_ms": self.config.poll_interval_ms,
            "devices": results,
            "system_utilization_pct": self.config.utilization_pct,
            "verdict": "SAFE" if all(r["is_safe"] for r in results) else "UNSAFE"
        }


class UnifiedPollingSimulator:
    """Simulates unified polling system behavior"""

    def __init__(self, config: PollingConfig):
        self.config = config
        self.latency_model = ApiLatencyModel(config)

    def analyze_current_vs_unified(self) -> Dict:
        """Compare current per-device polling vs unified polling"""
        # Current: Each device polls independently on its own thread
        current_cross_device_blocking = False  # Different devices don't block each other

        # Unified: All devices poll at same time
        unified_cross_device_blocking = False  # Still no blocking (different serial ports)

        # Key insight: Parallelism across devices is UNCHANGED
        # What changes is the TIMING - all polls start simultaneously

        return {
            "current_architecture": {
                "model": "Per-device independent threads",
                "cross_device_blocking": current_cross_device_blocking,
                "timing": "Devices poll at independent intervals (can be offset)",
                "advantage": "Natural load spreading if intervals are staggered",
                "disadvantage": "No control over alignment"
            },
            "unified_architecture": {
                "model": "Centralized scheduler triggers all devices simultaneously",
                "cross_device_blocking": unified_cross_device_blocking,
                "timing": "All devices start polling at exactly the same time",
                "advantage": "Predictable, synchronized updates for UI",
                "disadvantage": "Burst load every interval (CPU, if applicable)"
            },
            "verdict": "Both achieve same cross-device parallelism, unified has better predictability"
        }

    def recommend_polling_interval(self, target_staleness_ms: float = 500.0,
                                  max_utilization_pct: float = 50.0) -> Dict:
        """Recommend optimal polling interval for target staleness and utilization"""
        # Staleness requirement: poll_interval <= target_staleness_ms
        max_interval_for_staleness = target_staleness_ms

        # Utilization requirement: poll_duration / poll_interval <= max_utilization
        # Therefore: poll_interval >= poll_duration / max_utilization
        poll_duration = self.config.total_poll_duration_ms
        min_interval_for_utilization = poll_duration / (max_utilization_pct / 100)

        # Recommended interval must satisfy both constraints
        recommended_interval = max(min_interval_for_utilization, max_interval_for_staleness)

        # But not less than poll_duration (impossible to poll faster than execution time)
        recommended_interval = max(recommended_interval, poll_duration)

        # Calculate resulting metrics
        actual_utilization = (poll_duration / recommended_interval) * 100
        actual_staleness = recommended_interval

        return {
            "target_staleness_ms": target_staleness_ms,
            "target_max_utilization_pct": max_utilization_pct,
            "poll_duration_ms": poll_duration,
            "recommended_interval_ms": recommended_interval,
            "actual_utilization_pct": actual_utilization,
            "actual_staleness_ms": actual_staleness,
            "meets_staleness_target": actual_staleness <= target_staleness_ms,
            "meets_utilization_target": actual_utilization <= max_utilization_pct,
        }


def print_section(title: str, char: str = "="):
    """Print a section header"""
    print(f"\n{char * 80}")
    print(f"{title:^80}")
    print(f"{char * 80}\n")


def print_dict(data: Dict, indent: int = 0):
    """Pretty print a dictionary"""
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{' ' * indent}{key}:")
            print_dict(value, indent + 2)
        elif isinstance(value, list):
            print(f"{' ' * indent}{key}:")
            for item in value:
                if isinstance(item, dict):
                    print_dict(item, indent + 2)
                    print()
                else:
                    print(f"{' ' * (indent + 2)}- {item}")
        elif isinstance(value, bool):
            print(f"{' ' * indent}{key}: {'✓' if value else '✗'}")
        else:
            print(f"{' ' * indent}{key}: {value}")


def main():
    """Run unified polling analysis"""
    print_section("BenchMesh Unified Polling Analysis")

    print("This analysis explores unified parallel polling where all devices")
    print("are polled simultaneously at a single interval, and models the impact")
    print("on API responsiveness at different utilization levels.\n")

    # Define test scenarios
    scenarios = [
        {
            "name": "Conservative (50ms interval, ~35% utilization)",
            "config": PollingConfig(
                poll_interval_ms=50.0,
                devices=[
                    DeviceProfile("tenma-psu-1", num_channels=2, query_time_ms=8.7),
                    DeviceProfile("owon-spm-1", num_channels=1, query_time_ms=8.7),
                    DeviceProfile("owon-xdm-1", num_channels=1, query_time_ms=8.7),
                ]
            )
        },
        {
            "name": "Moderate (25ms interval, ~70% utilization)",
            "config": PollingConfig(
                poll_interval_ms=25.0,
                devices=[
                    DeviceProfile("tenma-psu-1", num_channels=2, query_time_ms=8.7),
                    DeviceProfile("owon-spm-1", num_channels=1, query_time_ms=8.7),
                    DeviceProfile("owon-xdm-1", num_channels=1, query_time_ms=8.7),
                ]
            )
        },
        {
            "name": "Aggressive (20ms interval, ~87% utilization)",
            "config": PollingConfig(
                poll_interval_ms=20.0,
                devices=[
                    DeviceProfile("tenma-psu-1", num_channels=2, query_time_ms=8.7),
                    DeviceProfile("owon-spm-1", num_channels=1, query_time_ms=8.7),
                    DeviceProfile("owon-xdm-1", num_channels=1, query_time_ms=8.7),
                ]
            )
        },
        {
            "name": "Extreme (18ms interval, ~97% utilization)",
            "config": PollingConfig(
                poll_interval_ms=18.0,
                devices=[
                    DeviceProfile("tenma-psu-1", num_channels=2, query_time_ms=8.7),
                    DeviceProfile("owon-spm-1", num_channels=1, query_time_ms=8.7),
                    DeviceProfile("owon-xdm-1", num_channels=1, query_time_ms=8.7),
                ]
            )
        },
    ]

    # Analysis 1: Current vs Unified Architecture
    print_section("1. Current vs Unified Polling Architecture", "-")
    simulator = UnifiedPollingSimulator(scenarios[0]["config"])
    arch_comparison = simulator.analyze_current_vs_unified()
    print_dict(arch_comparison)

    # Analysis 2: API Latency at Different Utilization Levels
    print_section("2. API Latency Analysis (Without Priority Queue)", "-")
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print(f"{'=' * 80}")
        config = scenario["config"]
        model = ApiLatencyModel(config)

        print(f"\nSystem Metrics:")
        print(f"  Poll Interval: {config.poll_interval_ms}ms")
        print(f"  Total Poll Duration: {config.total_poll_duration_ms}ms (in parallel)")
        print(f"  System Utilization: {config.utilization_pct:.1f}%")
        print(f"  System Idle: {config.idle_pct:.1f}%")

        print(f"\nAPI Latency per Device:")
        for device in config.devices:
            latency = model.calculate_latency_no_priority(device)
            print(f"\n  {device.device_id}:")
            print(f"    Best case: {latency['best_case_ms']:.1f}ms")
            print(f"    Average case: {latency['average_case_ms']:.1f}ms")
            print(f"    Worst case: {latency['worst_case_ms']:.1f}ms")
            print(f"    Blocking probability: {latency['blocking_probability']*100:.1f}%")
            print(f"    Expected wait: {latency['expected_wait_ms']:.1f}ms")

    # Analysis 3: API Latency WITH Priority Queue
    print_section("3. API Latency Analysis (With Priority Queue)", "-")
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print(f"{'=' * 80}")
        config = scenario["config"]
        model = ApiLatencyModel(config)

        print(f"\nSystem Utilization: {config.utilization_pct:.1f}%")

        print(f"\nNon-Preemptive Priority Queue:")
        for device in config.devices:
            latency = model.calculate_latency_with_priority(device, preemptive=False)
            print(f"\n  {device.device_id}:")
            print(f"    Best case: {latency['best_case_ms']:.1f}ms")
            print(f"    Average case: {latency['average_case_ms']:.1f}ms")
            print(f"    Worst case: {latency['worst_case_ms']:.1f}ms")
            print(f"    Expected wait: {latency['expected_wait_ms']:.1f}ms")

        print(f"\nPreemptive Priority Queue:")
        for device in config.devices:
            latency = model.calculate_latency_with_priority(device, preemptive=True)
            print(f"\n  {device.device_id}:")
            print(f"    Best case: {latency['best_case_ms']:.1f}ms")
            print(f"    Average case: {latency['average_case_ms']:.1f}ms")
            print(f"    Worst case: {latency['worst_case_ms']:.1f}ms (single query only!)")
            print(f"    Expected wait: {latency['expected_wait_ms']:.1f}ms")

    # Analysis 4: Maximum Safe Utilization
    print_section("4. Maximum Safe Utilization (for <50ms API latency)", "-")
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print(f"{'=' * 80}")
        config = scenario["config"]
        model = ApiLatencyModel(config)

        safety = model.calculate_max_safe_utilization(max_acceptable_latency_ms=50.0)
        print(f"\nTarget: API worst-case latency < {safety['max_acceptable_latency_ms']}ms")
        print(f"System utilization: {safety['system_utilization_pct']:.1f}%")
        print(f"Safety verdict: {safety['verdict']}")

        for dev in safety['devices']:
            print(f"\n  {dev['device_id']}:")
            print(f"    Current utilization: {dev['current_utilization_pct']:.1f}%")
            print(f"    Max safe utilization: {dev['max_safe_utilization_pct']:.1f}%")
            print(f"    Headroom: {dev['headroom_pct']:.1f}%")
            print(f"    Safe: {'✓' if dev['is_safe'] else '✗'}")

    # Analysis 5: Recommended Polling Intervals
    print_section("5. Recommended Polling Intervals", "-")

    targets = [
        {"staleness_ms": 500.0, "utilization_pct": 50.0},
        {"staleness_ms": 250.0, "utilization_pct": 50.0},
        {"staleness_ms": 100.0, "utilization_pct": 50.0},
        {"staleness_ms": 50.0, "utilization_pct": 50.0},
    ]

    base_config = PollingConfig(
        poll_interval_ms=100.0,  # Placeholder, will be recalculated
        devices=[
            DeviceProfile("tenma-psu-1", num_channels=2, query_time_ms=8.7),
            DeviceProfile("owon-spm-1", num_channels=1, query_time_ms=8.7),
            DeviceProfile("owon-xdm-1", num_channels=1, query_time_ms=8.7),
        ]
    )

    simulator = UnifiedPollingSimulator(base_config)

    for target in targets:
        print(f"\nTarget: <{target['staleness_ms']}ms staleness, <{target['utilization_pct']}% utilization")
        print(f"{'=' * 80}")
        recommendation = simulator.recommend_polling_interval(
            target_staleness_ms=target['staleness_ms'],
            max_utilization_pct=target['utilization_pct']
        )
        print_dict(recommendation, indent=2)

    # Final Recommendations
    print_section("FINAL RECOMMENDATIONS")

    print("Key Findings:\n")
    print("1. UNIFIED POLLING IS SAFE with proper prioritization")
    print("   - Cross-device parallelism is unchanged (different serial ports)")
    print("   - Synchronized timing provides predictable UI updates\n")

    print("2. WITHOUT PRIORITY QUEUE:")
    print("   - Conservative (35% util): Worst-case API latency ~26ms ✓")
    print("   - Moderate (70% util): Worst-case API latency ~26ms ✓")
    print("   - Aggressive (87% util): Worst-case API latency ~26ms ✓")
    print("   - Risk: API must wait for entire polling cycle\n")

    print("3. WITH NON-PREEMPTIVE PRIORITY QUEUE:")
    print("   - Same worst-case as without priority")
    print("   - But API jumps to front of queue (no subsequent polls block)")
    print("   - Recommended for moderate utilization (up to 70%)\n")

    print("4. WITH PREEMPTIVE PRIORITY QUEUE:")
    print("   - Worst-case API latency = 2x single query (~17ms)")
    print("   - Can push to 90%+ utilization safely")
    print("   - API only waits for current query, not entire poll cycle")
    print("   - BEST OPTION for aggressive polling\n")

    print("5. RECOMMENDED CONFIGURATION:")
    print("   - Implementation: Preemptive priority queue per device")
    print("   - Polling interval: 25-50ms (20-40 Hz updates)")
    print("   - Expected utilization: 35-70%")
    print("   - Guaranteed API latency: <20ms worst-case")
    print("   - UI staleness: 25-50ms (excellent real-time performance)\n")

    print("6. IMPLEMENTATION STRATEGY:")
    print("   - Phase 1: Unified polling scheduler (all devices trigger together)")
    print("   - Phase 2: Priority queue per device (API = HIGH, polling = LOW)")
    print("   - Phase 3: Preemptive scheduling (API can interrupt polling)")
    print("   - Phase 4: Fine-tune intervals based on real-world measurements\n")

    print("Conclusion:")
    print("  You CAN push polling to the limits (80-90% utilization) with preemptive")
    print("  priority queues. This will give you 20-50ms UI updates while keeping")
    print("  API latency under 20ms worst-case. The key is letting API requests")
    print("  interrupt ongoing polls after the current query completes.")

    print_section("Analysis Complete")


if __name__ == "__main__":
    main()
