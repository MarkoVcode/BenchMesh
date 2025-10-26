# Testing Guide

BenchMesh includes comprehensive testing infrastructure including unit tests, integration tests, E2E tests, and an MCP service for automated testing.

## Testing MCP Service

BenchMesh includes a comprehensive Model Context Protocol (MCP) service for automated testing. This service enables Claude Code to run tests automatically after code changes, supporting the project's TDD philosophy.

### Quick Start

```bash
# Install MCP service dependencies
cd mcp_services/testing
pip install -r requirements.txt --user

# Test the service
cd /home/marek/project/BenchMesh
python3 mcp_services/testing/client_helper.py
```

### Available Test Tools

The MCP service provides:
- **Backend Tests**: Run pytest tests with filtering (46 tests discovered)
- **Frontend Unit Tests**: Run vitest tests (21 tests discovered)
- **E2E Tests**: Run Playwright tests for UI integration testing (31 tests)
- **Integration Tests**: Run integration tests separately
- **Smart Testing**: Automatically run tests for changed files
- **Test Discovery**: Find all available tests
- **JSON Reports**: Structured test results with detailed metrics

### E2E Testing Modes

#### Mocked Tests (default)
Fast, isolated tests with mocked API/WebSocket

```bash
npm run test:e2e
```

#### Real Service Tests
Full integration tests against running backend

```bash
# 1. Start backend service
cd benchmesh-serial-service && PYTHONPATH=src uvicorn benchmesh_service.api:app --port 57666 &

# 2. Run E2E tests with real service
npm run test:e2e:service
```

### Usage Examples

```python
from mcp_services.testing.client_helper import test_all, test_backend, test_changed

# Run all tests
results = await test_all(verbose=True)

# Run specific backend tests
results = await test_backend("test_api_instruments.py")

# Test changed files
results = await test_changed([
    "benchmesh-serial-service/src/benchmesh_service/api.py"
])
```

### Documentation

See complete documentation:
- `mcp_services/testing/README.md` - Full MCP testing documentation
- `mcp_services/testing/QUICKSTART.md` - Quick start guide

## Frontend E2E Testing

The frontend includes comprehensive Playwright tests that verify UI functionality with mocked API and WebSocket connections.

### Test Coverage

Tests cover:
- App navigation and modals (Configuration, Documentation, Metrics, Recording)
- Instrument display and status indicators
- Device interaction and real-time updates
- API integration, error handling, and retry logic
- WebSocket connection and data streaming

### Running E2E Tests

```bash
# From benchmesh-serial-service/frontend/ directory

# Run E2E tests (Playwright)
npm run test:e2e

# Run E2E tests with UI mode
npm run test:e2e:ui

# Run E2E tests in headed mode (visible browser)
npm run test:e2e:headed

# Run E2E tests in debug mode
npm run test:e2e:debug
```

### E2E Documentation

See `benchmesh-serial-service/frontend/e2e/README.md` for detailed E2E testing documentation.

## Backend Testing

### Running Tests

```bash
# From benchmesh-serial-service/ directory

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_serial_manager.py

# Run with verbose output
pytest -v tests/
```

### Test Coverage

Tests cover:
- Manifest resolution
- Driver factory
- Serial manager behavior
- Concurrency
- Polling
- Edge cases

### Testing Strategy

- Mock serial communication using `unittest.mock.Mock` for transport
- Tests use `pytest` with fixtures in `conftest.py`
- Emphasis on integration and end-to-end tests
- Manual testability as a design goal
- Focus on critical path testing initially
- Add unit tests for complex logic and edge cases
- Testing pyramid: 60% unit, 30% integration, 10% end-to-end

## Frontend Unit Testing

### Running Tests

```bash
# From benchmesh-serial-service/frontend/ directory

# Run unit tests (vitest)
npm test

# Run unit tests once (CI mode)
npm run test:run

# Build for production
npm run build

# Preview production build
npm run preview
```

### Test Framework

- Frontend uses `vitest` with `@testing-library/react`

## CI Testing

GitHub Actions runs on all branches and PRs:
- Backend tests: `pytest benchmesh-serial-service/tests`
- Frontend tests: `npx vitest run --reporter=dot`

### Guidelines

- Apply TDD principles when adding new features
- Always MUST run tests after the code changes
- Always MUST cover new development with tests - whatever is added or improved
- Differentiate between unit tests and integration tests
  - Integration tests should NOT run in GitHub Actions (reserve for local/staging testing only)
- All new unit tests suitable for GitHub Actions execution must be automatically added to the CI workflow
- Always verify CI tests locally
- When implementing new feature always try to test on the real working service (particularly applies to serial service and API)
