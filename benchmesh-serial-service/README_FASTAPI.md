# BenchMesh Serial Service - FastAPI mode

Two ways to run the service:

1) Standalone SerialManager (legacy/debug)
   - poetry run python -m benchmesh_service.main --config ./config.yaml

2) FastAPI application
   - ENV: BENCHMESH_CONFIG=./config.yaml
   - poetry run uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 52892

API
- GET /status -> { "devices_total": N, "connected": M, "disconnected": N-M }

Notes
- The FastAPI app starts/stops SerialManager on app startup/shutdown.
- Keep BENCHMESH_CONFIG environment variable pointing to your config.yaml.
- To enable console DEBUG logs, adjust logger configuration if desired.
