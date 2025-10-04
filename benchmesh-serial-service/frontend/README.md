BenchMesh UI (React + TypeScript + Vite)

Development
- Node.js >= 18
- From this directory:
  - npm install
  - npm run dev

By default, the dev server runs on port 52893.
The FastAPI service is expected on port 57666.

Production build
- npm run build
- The build output appears under dist/

Integration with FastAPI
- The FastAPI app serves its own API at :57665.
- In development, Vite serves the UI on :52892 and the UI makes API calls to :57665.
- For a single-process run convenience, the FastAPI app can launch the Vite dev server as a background subprocess when started with --with-ui flag (see service README for details).
