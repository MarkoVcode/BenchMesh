# Release Testing Command

Perform a comprehensive pre-release test of the BenchMesh project.

## Tasks to perform:

1. **Start Services**
   - Start the backend and Node-RED services using ./start.sh
   - Wait for services to be fully initialized (check http://localhost:57666/instruments)

2. **Basic API Tests**
   - Test the /instruments endpoint
   - Test the /ui/ endpoint to verify frontend is served
   - Verify assets load correctly (check for 200 OK responses)

3. **Web Browser Application Test**
   - Verify the UI loads at http://localhost:57666/ui/
   - Check that the HTML contains correct asset references
   - Verify the API is accessible from the UI
   - Check that instruments are displayed correctly
   - Verify WebSocket registry connection is active

4. **Node-RED Integration Test**
   - Verify Node-RED is accessible at http://localhost:1880
   - Test custom BenchMesh nodes are installed and available:
     - benchmesh-automation (controllable timer)
     - benchmesh-dmm (DMM reading)
     - benchmesh-ell (Electronic load control)
     - benchmesh-psu (Power supply control)
     - benchmesh-threshold (Threshold comparison)
     - benchmesh-instrument (Generic instrument)
   - Test automation API endpoints:
     - GET http://localhost:1880/benchmesh/automations (should return automation status)
     - Verify response contains automation details when automations are deployed
   - Verify UI automation integration:
     - Check Node-RED Automations button shows correct status (🔴 RED when running, 🟢 GREEN when stopped)
     - Verify automation counter badge shows "X/Y running" format
     - Test button opens Node-RED in new tab
   - Import and test example flow:
     - Load /docs/node-red/examples/do-not-allow-overcharge.json
     - Verify flow uses custom BenchMesh nodes
     - Deploy flow and verify automation starts
     - Check that automation appears in UI with correct count

5. **ETag Performance Test**
   - Test /instruments endpoint caching:
     - First request should return 200 with ETag header
     - Subsequent requests with If-None-Match should return 304 when data unchanged
     - Verify UI doesn't re-render when receiving 304 responses
   - Monitor network traffic to confirm reduced payload

6. **Electron Application Test**
   - Build the frontend if not already built
   - Start Electron in development mode (NODE_ENV=development npm start from /electron)
   - Monitor logs to confirm:
     - Backend is found and ready
     - UI loads successfully
     - Assets load with 200 OK status
     - API calls are successful
   - Stop Electron after verification

7. **Run All Tests**
   - Run frontend tests: `cd benchmesh-serial-service/frontend && npm run test:run`
   - Run backend tests: `cd benchmesh-serial-service && python3 -m pytest -q tests`
   - Report any failures

8. **Cleanup**
   - Kill all background processes (./start.sh, Electron, etc.)
   - Verify all services are stopped

9. **Issue Detection and Fixes**
   - If any issues are detected during testing:
     - Identify the root cause
     - Propose specific fixes
     - Ask user if they want to apply the fixes
   - If all tests pass, confirm the project is ready for release

## Success Criteria:
- All services start successfully
- API endpoints respond correctly
- Web UI loads and functions
- Node-RED integration works:
  - All custom BenchMesh nodes are available
  - Automation API endpoints respond correctly
  - UI shows automation status correctly
  - Example flow can be imported and deployed
- ETag caching works (304 responses when data unchanged)
- Electron app loads and functions
- All unit tests pass (frontend and backend)
- All processes cleaned up properly
