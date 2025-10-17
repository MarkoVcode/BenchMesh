# Manifest Polling Configuration Pattern

This document describes the standardized polling configuration patterns used in BenchMesh driver manifests.

## Overview

BenchMesh supports two polling patterns based on the device architecture:

1. **Class-Level Polling** - For single-class devices
2. **Device-Level Unified Polling** - For multi-class devices sharing a serial port

## Pattern 1: Single-Class Devices (Class-Level Polling)

### When to Use
- Device implements ONE instrument class only (e.g., only PSU, only DMM, only ELL)
- Device has dedicated polling method for that class

### Manifest Structure
```json
{
  "models": {
    "MODEL_NAME": {
      "classes": ["PSU"],
      "instrument_class": {
        "PSU": {
          "pooling": [
            {
              "method": "poll_status",
              "interval": 2.0
            }
          ],
          "ui_component": "GenericPSU",
          "features": { }
        }
      }
    }
  }
}
```

### Examples
- **tenma_72**: PSU class only
- **owon_xdm**: DMM class only
- **owon_oel**: ELL (Electronic Load) class only
- **owon_dge**: AWG (Function Generator) class only

### Behavior
- Polling method defined at class level
- Each class polled independently with its own interval
- Worker calls class-specific poll method (e.g., `poll_status()`)

## Pattern 2: Multi-Class Devices (Device-Level Unified Polling)

### When to Use
- Device implements MULTIPLE instrument classes (e.g., both PSU and DMM)
- All classes share a SINGLE serial port
- Want to avoid multiple serial operations per poll cycle

### Manifest Structure
```json
{
  "models": {
    "MODEL_NAME": {
      "classes": ["PSU", "DMM"],
      "pooling": [
        {
          "method": "poll_status",
          "interval": 1.0,
          "multi_class": true
        }
      ],
      "instrument_class": {
        "PSU": {
          "ui_component": "GenericPSU",
          "features": { }
        },
        "DMM": {
          "ui_component": "GenericDMM",
          "features": { }
        }
      }
    }
  }
}
```

### Key Differences
- Polling defined at **device level** (outside `instrument_class`)
- **No polling** entries in individual class definitions
- Must include `"multi_class": true` flag
- Driver must implement unified `poll_status()` method

### Driver Requirements
The driver MUST implement a `poll_status(channel)` method that returns class-keyed data:

```python
def poll_status(self, channel: int):
    """
    Unified polling for multi-class device.
    Returns dict keyed by class name.
    """
    return {
        "PSU": {
            "VOUT": 12.0,
            "IOUT": 1.5,
            "POUT": 18.0,
            ...
        },
        "DMM": {
            "measurement1_num": "3.30",
            "measurement1_symbol": "V",
            "measurement1_function": "VOLT:DC"
        }
    }
```

### Examples
- **owon_spm (SPM3103)**: Implements both PSU and DMM classes on single serial port

### Behavior
- Single poll method called once per interval
- Returns data for ALL classes in one serial operation
- Worker distributes results to appropriate class registries
- Prevents queue saturation from multiple class polls

## Benefits of Unified Polling

For multi-class devices sharing a serial port:

1. **50-70% fewer serial operations**
   - Before: 2 polls per cycle (PSU poll + DMM poll)
   - After: 1 poll per cycle (unified poll)

2. **Eliminates queue saturation**
   - Before: 30,701+ skipped polls due to queue depth
   - After: Zero queue depth warnings

3. **Better data accuracy**
   - PSU and DMM readings from the same moment in time
   - No timing skew between class readings

4. **Aligns with hardware reality**
   - One serial port = one communication channel
   - Reflects physical constraints in software architecture

## Migration Guide

### Converting Single-Class to Multi-Class

If you need to add a new class to an existing device:

1. Move `pooling` from class level to device level
2. Add `multi_class: true` flag
3. Update driver to implement unified `poll_status()` returning class-keyed dict
4. Keep individual class definitions but remove their `pooling` entries
5. Test thoroughly to verify both classes receive data

### Example Conversion

**Before (single-class):**
```json
"instrument_class": {
  "PSU": {
    "pooling": [{"method": "poll_status", "interval": 2}],
    ...
  }
}
```

**After (adding DMM class):**
```json
"pooling": [
  {"method": "poll_status", "interval": 2, "multi_class": true}
],
"instrument_class": {
  "PSU": { /* no pooling here */ },
  "DMM": { /* no pooling here */ }
}
```

## Verification

To verify polling configuration:

```bash
# Check which devices use multi-class polling
grep -r "multi_class" benchmesh-serial-service/src/benchmesh_service/drivers/*/manifest.json

# Monitor queue depth for devices
tail -f logs/benchmesh_service.log | grep "queue depth"

# Check metrics summary
tail -f logs/benchmesh_service.log | grep -A 20 "Metrics Summary"
```

## See Also

- `poll_worker.py` - Implementation of polling logic
- `manifest_resolver.py` - Manifest parsing and polling configuration resolution
- `UNIFIED_POLLING_DESIGN.md` - Overall unified polling architecture
