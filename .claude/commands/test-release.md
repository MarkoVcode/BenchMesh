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

4. **Electron Application Test**
   - Build the frontend if not already built
   - Start Electron in development mode (NODE_ENV=development npm start from /electron)
   - Monitor logs to confirm:
     - Backend is found and ready
     - UI loads successfully
     - Assets load with 200 OK status
     - API calls are successful
   - Stop Electron after verification

5. **Run All Tests**
   - Run frontend tests: `cd benchmesh-serial-service/frontend && npm run test:run`
   - Run backend tests: `cd benchmesh-serial-service && python3 -m pytest -q tests`
   - Report any failures

6. **Cleanup**
   - Kill all background processes (./start.sh, Electron, etc.)
   - Verify all services are stopped

7. **Issue Detection and Fixes**
   - If any issues are detected during testing:
     - Identify the root cause
     - Propose specific fixes
     - Ask user if they want to apply the fixes
   - If all tests pass, confirm the project is ready for release

## Success Criteria:
- All services start successfully
- API endpoints respond correctly
- Web UI loads and functions
- Electron app loads and functions
- All unit tests pass (frontend and backend)
- All processes cleaned up properly
