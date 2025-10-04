# Serial Manager Architecture

This service manages serial instruments with the following components:

- SerialManager (composition root)
  - Wires subcomponents and starts per-device workers
- ManifestResolver
  - Parses manifests to answer:
    - classes per device, channels per class
    - per-class polling method and interval
    - per-model connection EOLs (seol/reol)
- DriverFactory
  - Loads driver class for a driver key
- DeviceConnection
  - Wraps a driver instance; handles identify-only attempts and timestamps for reconnect cadence
- DeviceWorker (PollScheduler)
  - Schedules and executes per-class/channel polling and writes to DeviceRegistry
- DeviceRegistry
  - Maintains in-memory state: IDN, per-class status by channel
- Clock
  - Provides now(); ManualClock for deterministic tests

UML (simplified):

```
+------------------+        uses        +-------------------+
|  SerialManager   |------------------->| ManifestResolver  |
| - devices        |                    +-------------------+
| - connections    |        uses        +-------------------+
| - registry       |------------------->|  DriverFactory    |
| - clock          |        uses        +-------------------+
| - workers        |------------------->| DeviceRegistry    |
|                  |        uses        +-------------------+
| start()/stop()   |------------------->| DeviceConnection  |
|                  |        composes    +-------------------+
|                  |------------------->|  DeviceWorker     |
+------------------+                    +-------------------+
```

Flow:
1. SerialManager creates a driver via DriverFactory and wraps it in DeviceConnection.
2. On connect, identify() is attempted; IDN is written to DeviceRegistry.
3. DeviceWorker runs per-class polling based on ManifestResolver (method, interval, channels).
4. Empty/error polls clear IDN and per-class statuses; DeviceConnection will attempt re-identify.

Extensibility:
- ReconnectPolicy/IdentifyStrategy can be added to DeviceConnection.
- Metrics hooks can be inserted at DeviceWorker and DeviceConnection boundaries.
