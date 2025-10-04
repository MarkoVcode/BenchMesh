# BenchMesh Serial Service - FastAPI + UI

You can run the FastAPI app and the React UI together. The API also exposes a WebSocket streaming the registry at 100 ms.

Run in development
- Node 18+ installed for UI
- Python env (poetry or requirements.txt)

Steps
1) Backend
   - export BENCHMESH_CONFIG=./config.yaml
   - poetry run uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 57666
   - The API will attempt to auto-start the Vite dev server if BENCHMESH_START_UI=1 and frontend/node_modules exists

2) Frontend (first time only)
   - cd benchmesh-serial-service/frontend
   - npm install
   - npm run dev (dev server at http://localhost:52892)

UI access
- Navigate to http://localhost:57665/ — you’ll be redirected to UI (either built /ui or dev server)

Endpoints used by UI
- GET /instruments -> list of instruments with IDN and class channels
- WS /ws/registry -> live registry JSON pushed every 100 ms

Production build
- cd benchmesh-serial-service/frontend && npm run build
- Restart API; built UI is served at /ui

Notes
- CORS is enabled on API for development
- Set BENCHMESH_START_UI=0 to disable auto-start of the dev server
