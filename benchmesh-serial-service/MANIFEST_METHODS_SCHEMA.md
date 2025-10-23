# Manifest Methods Schema

This document describes the optional `methods` section that can be added to driver manifests to enrich API method discovery with detailed metadata.

## Overview

The BenchMesh API automatically discovers all `query_*` and `set_*` methods on drivers using Python introspection. This provides automatic method listing with basic information (name, parameters, types).

However, drivers can optionally define a `methods` section in their `manifest.json` to provide:
- Human-friendly descriptions
- Parameter units and value ranges
- Return value units
- Custom examples

This enrichment is **completely optional** - the API will work without it, but it provides better documentation for users and dynamic UIs (e.g., Node-RED).

## Schema Structure

### Top-Level `methods` Section

Add this at the same level as `models` in your manifest:

```json
{
  "vendor": "TENMA",
  "family": "72",
  "version": "1.0.0",
  "models": {
    "DEFAULT": {
      ...
    }
  },
  "methods": {
    "query_method_name": { ... },
    "set_method_name": { ... }
  }
}
```

### Method Entry Schema

Each method can define:

```json
{
  "methods": {
    "query_output_voltage": {
      "description": "Query the actual output voltage being delivered",
      "parameters": {
        "channel": {
          "description": "PSU channel number",
          "range": [1, 3],
          "unit": null
        }
      },
      "returns": {
        "type": "float",
        "unit": "V",
        "precision": 0.01
      },
      "example": "GET /instruments/PSU/psu-1/1/output_voltage"
    },
    "set_voltage": {
      "description": "Set voltage setpoint for the PSU channel",
      "parameters": {
        "channel": {
          "description": "PSU channel number",
          "range": [1, 3]
        },
        "value": {
          "description": "Target voltage setpoint",
          "unit": "V",
          "range": [0.0, 30.0],
          "precision": 0.01
        }
      },
      "example": "POST /instruments/PSU/psu-1/1/voltage/12.5"
    }
  }
}
```

### Field Descriptions

#### Method Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | No | Human-friendly description of what the method does. If omitted, auto-generated from method name. |
| `parameters` | object | No | Dict of parameter enrichment data keyed by parameter name |
| `returns` | object | No | Return value metadata (type, unit, precision) |
| `example` | string | No | Custom example API call. If omitted, auto-generated. |

#### Parameter Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | No | Human-friendly description of the parameter |
| `unit` | string | No | Physical unit (e.g., "V", "A", "W", "°C") |
| `range` | array | No | Valid value range as `[min, max]` |
| `precision` | number | No | Smallest meaningful increment (e.g., 0.01 for 2 decimal places) |

#### Returns Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | No | Return type override (e.g., "float", "int", "string", "boolean") |
| `unit` | string | No | Physical unit of return value |
| `precision` | number | No | Smallest meaningful increment |

## Auto-Generated Defaults

If you don't provide manifest enrichment, the API will auto-generate:

| Field | Auto-Generated Value |
|-------|---------------------|
| Description | `query_output_voltage` → "Query the output voltage" |
| Parameter description | `channel` → "Channel parameter" |
| Parameter type | From Python type hints if present, else "any" |
| Example | `GET /instruments/PSU/psu-1/1/output_voltage` |

## Example: Full TENMA PSU Manifest Methods

```json
{
  "vendor": "TENMA",
  "family": "72",
  "version": "1.0.0",
  "models": {
    "DEFAULT": {
      "classes": ["PSU"],
      "connection": {
        "seol": "",
        "reol": ""
      },
      "instrument_class": {
        "PSU": {
          "ui_component": "GenericPSU",
          "features": {
            "channels": 1,
            "absolute_limits": {
              "voltage": {"unit": "V", "max": 30.0},
              "current": {"unit": "A", "max": 5.0}
            }
          }
        }
      }
    }
  },
  "methods": {
    "query_output_voltage": {
      "description": "Query the actual output voltage being delivered",
      "parameters": {
        "channel": {
          "description": "PSU channel number",
          "range": [1, 1]
        }
      },
      "returns": {
        "type": "float",
        "unit": "V",
        "precision": 0.01
      }
    },
    "query_output_current": {
      "description": "Query the actual output current being delivered",
      "parameters": {
        "channel": {
          "description": "PSU channel number",
          "range": [1, 1]
        }
      },
      "returns": {
        "type": "float",
        "unit": "A",
        "precision": 0.001
      }
    },
    "set_voltage": {
      "description": "Set voltage setpoint for the PSU output",
      "parameters": {
        "channel": {
          "description": "PSU channel number",
          "range": [1, 1]
        },
        "value": {
          "description": "Target voltage",
          "unit": "V",
          "range": [0.0, 30.0],
          "precision": 0.01
        }
      }
    },
    "set_current": {
      "description": "Set current limit for the PSU output",
      "parameters": {
        "channel": {
          "description": "PSU channel number",
          "range": [1, 1]
        },
        "value": {
          "description": "Current limit",
          "unit": "A",
          "range": [0.0, 5.0],
          "precision": 0.001
        }
      }
    },
    "set_output": {
      "description": "Enable or disable the PSU output",
      "parameters": {
        "channel": {
          "description": "PSU channel number",
          "range": [1, 1]
        },
        "value": {
          "description": "Output state",
          "enum": ["ON", "OFF"]
        }
      }
    }
  }
}
```

## API Response Format

When the `/instruments/{class}/{device_id}/methods` endpoint is called, it returns:

```json
{
  "device_id": "psu-1",
  "class": "PSU",
  "methods": [
    {
      "name": "output_voltage",
      "full_name": "query_output_voltage",
      "http_method": "GET",
      "description": "Query the actual output voltage being delivered",
      "parameters": [
        {
          "name": "channel",
          "type": "int",
          "required": true,
          "default": null,
          "description": "PSU channel number",
          "range": [1, 1]
        }
      ],
      "returns": "float",
      "returns_unit": "V",
      "example": "GET /instruments/PSU/psu-1/1/output_voltage"
    }
  ]
}
```

## Best Practices

1. **Start without manifest enrichment** - The auto-generated data is often sufficient
2. **Add enrichment incrementally** - Start with descriptions for most commonly used methods
3. **Focus on user-facing methods** - Skip enriching internal/debugging methods
4. **Keep descriptions concise** - One-line descriptions work best in UIs
5. **Always specify units** - Critical for physical measurements (V, A, W, °C, etc.)
6. **Use value ranges** - Helps UI validation and prevents user errors
7. **Match driver limits** - Ensure manifest ranges match what the driver actually supports

## Migration Path

Existing drivers work without any changes. To add enrichment:

1. Add `methods` section to `manifest.json`
2. Define entries for high-value methods first
3. Test with `/instruments/{class}/{device_id}/methods` endpoint
4. Iterate based on user feedback

The API will seamlessly merge manifest data with introspected data, falling back to auto-generated values for any missing enrichment.
