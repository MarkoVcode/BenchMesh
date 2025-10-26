# Adaptive Throttling System

**Status**: Implemented (Phases 1-4 Complete)

The adaptive throttling system provides intelligent, self-healing connection management for serial devices. It prevents connection failures by automatically adjusting polling behavior based on device health, transport capabilities, and queue pressure.

## Table of Contents

- [Overview](#overview)
- [Phase 1: Core Throttling](#phase-1-core-throttling)
- [Phase 2: Transport-Specific Limits](#phase-2-transport-specific-limits)
- [Phase 3: Enhanced Quality Scoring](#phase-3-enhanced-quality-scoring)
- [Phase 4: Monitoring & Metrics](#phase-4-monitoring--metrics)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

## Overview

The adaptive throttling system implements a 5-layer defense strategy:

1. **Gradual Queue Depth Throttling**: Smooth degradation instead of cliff-edge failures
2. **Exponential Backoff**: Automatic slowdown on consecutive failures (2x, 4x, 8x)
3. **Connection Quality Scoring**: Trend-based adaptation with weighted recent history
4. **Transport-Specific Limits**: Different thresholds for USB TMC, Serial, TCP/IP
5. **Automatic Feedback Loop**: Self-healing recovery when conditions improve

**Key Benefits:**
- ✅ Prevents connection crashes without manual intervention
- ✅ Maintains maximum safe speed for each transport type
- ✅ Self-heals automatically when quality improves
- ✅ Provides detailed metrics for monitoring
- ✅ Enabled by default for backward compatibility

## Phase 1: Core Throttling

**Implemented**: January 2025

### Features

#### 1. Gradual Queue Depth Throttling

Instead of all-or-nothing throttling, the system uses probabilistic throttling based on queue fullness:

- **0-30% full**: No throttling (100% poll rate)
- **30-60% full**: 25% skip probability (75% poll rate)
- **60-80% full**: 50% skip probability (50% poll rate)
- **80-100% full**: 75% skip probability (25% poll rate)
- **>100% overflow**: 100% skip (stop polling until queue drains)

This provides **smooth degradation** instead of sudden stops.

#### 2. Exponential Backoff

On consecutive failures, the polling interval increases exponentially:

- **1st failure**: 2x interval (e.g., 2s → 4s)
- **2nd failure**: 4x interval (e.g., 2s → 8s)
- **3rd failure**: 8x interval (e.g., 2s → 16s - capped)

Resets to 1x on successful poll.

#### 3. Connection Quality Monitoring

Tracks rolling window of last 20 operations:
- **Success**: +5 points
- **Timeout**: -10 points
- **Error**: -15 points

Quality score normalized to 0-100 scale.

#### 4. Automatic Recovery

Dead devices are retried every 30 seconds with circuit breaker pattern.

### Configuration (Phase 1)

```bash
# Enable/disable adaptive throttling (default: enabled)
export BM_ADAPTIVE_THROTTLING=true

# Queue depth throttling start threshold (default: 0.3 = 30%)
export BM_QUEUE_THROTTLE_START=0.3

# Number of throttle tiers (default: 4)
export BM_QUEUE_THROTTLE_TIERS=4

# Backoff multiplier on failure (default: 2.0)
export BM_BACKOFF_MULTIPLIER=2.0

# Maximum backoff multiplier cap (default: 8.0)
export BM_BACKOFF_MAX_MULTIPLIER=8.0

# Recovery interval for dead devices in ms (default: 30000)
export BM_RECOVERY_INTERVAL_MS=30000

# Quality monitoring window size (default: 20 operations)
export BM_QUALITY_WINDOW_SIZE=20
```

## Phase 2: Transport-Specific Limits

**Implemented**: January 2025

Different physical transports have different characteristics and require different limits:

### USB TMC (IEEE 488.2 over USB)

**Characteristics**: More fragile, smaller kernel buffers, sensitive to command flooding

```bash
# Minimum safe polling interval (default: 1000ms)
export BM_USBTMC_MIN_INTERVAL=1000

# Recommended interval (default: 2000ms)
export BM_USBTMC_RECOMMENDED_INTERVAL=2000

# Max queue depth (default: 5 - lower tolerance)
export BM_USBTMC_MAX_QUEUE_DEPTH=5

# Timeout multiplier (default: 1.5x - longer timeouts)
export BM_USBTMC_TIMEOUT_MULT=1.5
```

### Serial (RS232/USB-Serial)

**Characteristics**: More forgiving, standard buffering

```bash
# Minimum safe polling interval (default: 500ms)
export BM_SERIAL_MIN_INTERVAL=500

# Recommended interval (default: 1000ms)
export BM_SERIAL_RECOMMENDED_INTERVAL=1000

# Max queue depth (default: 10 - standard)
export BM_SERIAL_MAX_QUEUE_DEPTH=10

# Timeout multiplier (default: 1.0x - normal)
export BM_SERIAL_TIMEOUT_MULT=1.0
```

### TCP/IP (Network SCPI)

**Characteristics**: Network latency, higher buffering capacity

```bash
# Minimum safe polling interval (default: 500ms)
export BM_TCPIP_MIN_INTERVAL=500

# Recommended interval (default: 1000ms)
export BM_TCPIP_RECOMMENDED_INTERVAL=1000

# Max queue depth (default: 15 - higher buffering)
export BM_TCPIP_MAX_QUEUE_DEPTH=15

# Timeout multiplier (default: 2.0x - network latency)
export BM_TCPIP_TIMEOUT_MULT=2.0
```

### How It Works

The system automatically detects transport type from `config.yaml` and applies appropriate limits:

```yaml
devices:
  - id: rigol-dho804
    name: "RIGOL Oscilloscope"
    driver: rigol_dho800
    transport: usbtmc  # Auto-detected: uses USB TMC limits
    port: /dev/tmcDHO804

  - id: tenma-psu
    name: "TENMA PSU"
    driver: tenma_72
    port: /dev/tty722540  # No transport specified: defaults to 'serial'
```

## Phase 3: Enhanced Quality Scoring

**Implemented**: January 2025

### Features

#### 1. Weighted Recent History

Recent operations are weighted more heavily (2.0x by default) than older operations in the rolling window. This makes the system more responsive to **recent changes** in connection quality.

- **Recent 25% of window**: 2.0x weight
- **Older 75% of window**: 1.0x weight

#### 2. Trend Detection

Uses linear regression on last 10 quality scores to detect trends:

- **Improving**: Slope > +2 points/step
- **Stable**: Slope between -2 and +2
- **Degrading**: Slope < -2 points/step

#### 3. Quality Tiers with Speed Multipliers

| Tier | Score Range | Speed Multiplier | Description |
|------|-------------|------------------|-------------|
| Excellent | 95-100 | 1.0x | Full speed |
| Good | 80-95 | 0.9x | Slight slowdown |
| Fair | 60-80 | 0.7x | Moderate slowdown |
| Poor | 40-60 | 0.5x | Significant slowdown |
| Critical | <40 | 0.25x | Severe slowdown |

#### 4. Quality Threshold Triggers

- **Warning**: Quality is "poor" or "critical" AND degrading
- **Critical**: Quality is "critical" tier

These can trigger automated responses or alerts.

### Example Scenario

```
Initial state:
- Quality: 50 (poor), trend: stable, multiplier: 0.5x
- Polling at: 2.0s × 1.0 (backoff) × 0.5 (quality) = 1.0s

After 3 consecutive failures:
- Quality: 30 (critical), trend: degrading, multiplier: 0.25x
- Backoff: 8.0x (capped at max)
- Polling at: 2.0s × 8.0 × 0.25 = 4.0s

After recovery (5 successful polls):
- Quality: 70 (fair), trend: improving, multiplier: 0.7x
- Backoff: 1.0x (reset)
- Polling at: 2.0s × 1.0 × 0.7 = 1.4s
```

## Phase 4: Monitoring & Metrics

**Implemented**: January 2025

### Metrics Collected

The system exports comprehensive metrics for monitoring:

**Performance Metrics:**
- Utilization % (time spent in serial I/O)
- QPS (queries per second)
- API latency percentiles (P95, P99)
- Average queue depth
- Average poll duration

**Throttling Metrics:**
- Throttle events count (polls skipped)
- Throttle skip rate %
- Current backoff multiplier
- Connection quality score (0-100)
- Quality tier (excellent/good/fair/poor/critical)
- Quality trend (improving/stable/degrading)
- Transport type (serial/usbtmc/tcpip)

### Metrics Logging

Metrics are automatically logged every 30 seconds:

```
================================================================================
Serial Port Utilization Metrics Summary
================================================================================

Device: rigol-dho804 (USBTMC)
  Window Duration: 30.0s
  Utilization: 12.5%
  QPS: 0.50
  Total Operations: 15
  API Requests: 2
  API Latency P95: 245.32ms
  API Latency P99: 267.89ms
  Avg Queue Depth: 1.2
  Avg Poll Duration: 150.23ms
  Throttle Events: 3 (16.7% skip rate)
  Backoff Multiplier: 2.0x
  Quality: good (score: 85.0, trend: stable)

Device: tenma-psu (SERIAL)
  Window Duration: 30.0s
  Utilization: 8.3%
  QPS: 1.00
  Total Operations: 30
  API Requests: 5
  Quality: excellent (score: 98.5, trend: improving)
================================================================================
```

## API Endpoints

### GET /metrics

Get metrics summary for all devices.

**Response:**
```json
{
  "summary": {
    "rigol-dho804": {
      "device_id": "rigol-dho804",
      "window_duration_s": 30.0,
      "utilization_pct": 12.5,
      "qps": 0.5,
      "api_request_count": 2,
      "api_latency_p95_ms": 245.32,
      "api_latency_p99_ms": 267.89,
      "avg_queue_depth": 1.2,
      "avg_poll_duration_ms": 150.23,
      "total_operations": 15,
      "throttle_events": 3,
      "throttle_rate_pct": 16.7,
      "backoff_multiplier": 2.0,
      "quality_score": 85.0,
      "quality_tier": "good",
      "quality_trend": "stable",
      "transport_type": "usbtmc"
    }
  },
  "timestamp": 1736274123.456
}
```

### GET /metrics/{device_id}

Get metrics for a specific device.

**Example:** `GET /metrics/rigol-dho804`

**Response:**
```json
{
  "device_id": "rigol-dho804",
  "window_duration_s": 30.0,
  "utilization_pct": 12.5,
  "qps": 0.5,
  "throttle_events": 3,
  "throttle_rate_pct": 16.7,
  "backoff_multiplier": 2.0,
  "quality_score": 85.0,
  "quality_tier": "good",
  "quality_trend": "stable",
  "transport_type": "usbtmc",
  "timestamp": 1736274123.456
}
```

## Configuration

### Manifest Polling Interval

The `interval` in driver `manifest.json` represents the **target interval when healthy**:

```json
{
  "polling": [
    {
      "method": "poll_status",
      "interval": 2.0  // Target: poll every 2 seconds when healthy
    }
  ]
}
```

The **effective interval** is dynamically adjusted:

```
effective_interval = base_interval × backoff_multiplier × quality_multiplier
```

**Examples with `interval: 2.0`:**
- Healthy: `2.0s × 1.0 × 1.0 = 2.0s`
- 1 failure: `2.0s × 2.0 × 0.9 = 3.6s`
- 3 failures: `2.0s × 8.0 × 0.5 = 8.0s`
- Poor quality: `2.0s × 1.0 × 0.25 = 0.5s`

**The system does NOT target utilization percentage.** Instead, it:
- Starts at manifest interval when healthy
- Backs off when stressed
- Self-adjusts to maintain stability

### Complete Configuration Reference

See `benchmesh-serial-service/src/benchmesh_service/settings.py` for all configuration options.

## Troubleshooting

### High Throttle Rate

**Symptoms**: Throttle events > 20% skip rate

**Causes:**
- Queue depth consistently high
- Polling interval too aggressive for transport type
- Device responding slowly

**Solutions:**
1. Check metrics: `GET /metrics/{device_id}`
2. Increase manifest polling interval
3. Verify transport type is correctly set
4. Check device health and connection quality

### Backoff Multiplier Stuck at Maximum

**Symptoms**: Backoff multiplier remains at 8.0x

**Causes:**
- Device continuously failing
- Connection physically broken
- Driver polling method broken

**Solutions:**
1. Check physical connection
2. Verify device is powered on
3. Test with driver CLI: `python -m benchmesh_service.tools.driver_cli`
4. Check logs for specific error messages

### Quality Score Degrading

**Symptoms**: Quality tier drops to "poor" or "critical"

**Causes:**
- Intermittent connection issues
- Transport buffer overflows
- Device overheating or malfunctioning

**Solutions:**
1. Monitor quality trend via `/metrics` endpoint
2. Check for pattern in degradation (time-based, operation-based)
3. Reduce polling frequency if USB TMC device
4. Verify device is functioning correctly

### Disabling Adaptive Throttling

If you need to disable the adaptive throttling system:

```bash
export BM_ADAPTIVE_THROTTLING=false
```

**⚠️ Warning**: Disabling adaptive throttling removes automatic protection against connection failures. Only disable for debugging purposes.

## See Also

- `ai_context/UNIFIED_POLLING_QUICKREF.md` - Unified polling system overview
- `ai_context/METRICS_MONITORING.md` - Metrics collection details
- `ai_context/TRANSPORT_LAYER_GUIDE.md` - Transport layer documentation
