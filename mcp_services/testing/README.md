# BenchMesh Testing MCP Service

A comprehensive Model Context Protocol (MCP) service for running tests in the BenchMesh project.

## Features

- **Backend Tests**: Run pytest tests with filtering, markers, and verbose output
- **Frontend Tests**: Run vitest tests with coverage support
- **Integration Tests**: Run integration tests separately (marked with `@pytest.mark.integration`)
- **Electron Tests**: Support for Electron app testing
- **Test Discovery**: Find all available tests without running them
- **Smart Testing**: Run only tests affected by changed files
- **JSON Reporting**: Structured test results with detailed reports

## Installation

1. Install dependencies:
```bash
cd mcp_services/testing
pip install -r requirements.txt
```

2. Configure Claude Code to use this MCP service by adding to your Claude Code MCP settings:
```json
{
  "mcpServers": {
    "benchmesh-testing": {
      "command": "python3",
      "args": ["/home/marek/project/BenchMesh/mcp_services/testing/server.py"]
    }
  }
}
```

## Available Tools

### run_backend_tests
Run backend pytest tests with optional filtering.

**Parameters:**
- `test_path` (optional): Specific test file or directory relative to `tests/`
- `verbose` (optional): Enable verbose output (default: false)
- `markers` (optional): Pytest markers to filter tests (e.g., "integration", "unit")

**Example:**
```json
{
  "test_path": "test_api_instruments.py",
  "verbose": true
}
```

### run_frontend_tests
Run frontend vitest tests.

**Parameters:**
- `watch` (optional): Run in watch mode (default: false)
- `coverage` (optional): Generate coverage report (default: false)

**Example:**
```json
{
  "coverage": true
}
```

### run_integration_tests
Run only integration tests (marked with `@pytest.mark.integration`).

**Parameters:**
- `test_path` (optional): Specific test file or directory

**Example:**
```json
{
  "test_path": "test_serial_manager_integration.py"
}
```

### run_electron_tests
Run Electron app tests.

**Parameters:** None

### run_e2e_tests
Run Playwright E2E tests for the frontend UI.

**Parameters:**
- `headed` (optional): Run tests in headed mode (visible browser) (default: false)
- `ui_mode` (optional): Run tests in interactive UI mode (default: false)
- `test_pattern` (optional): Test file pattern to run (e.g., "app-navigation.spec.ts")

**Example:**
```json
{
  "headed": true,
  "test_pattern": "app-navigation.spec.ts"
}
```

**Note**: By default, E2E tests run with mocked API/WebSocket. For testing with real backend service, use the `with-service/` test directory which requires the service to be running on port 57666

### run_all_tests
Run all tests (backend + frontend).

**Parameters:**
- `verbose` (optional): Enable verbose output (default: false)

**Example:**
```json
{
  "verbose": true
}
```

### discover_tests
Discover all available tests without running them.

**Parameters:** None

**Example Response:**
```json
{
  "backend": {
    "output": "test_api_instruments.py::test_get_instrument_method_success\n...",
    "count": 46
  },
  "frontend": {
    "output": "GenericPSU.test.tsx\n...",
    "count": 12
  }
}
```

### run_changed_tests
Run tests for changed files.

**Parameters:**
- `changed_files`: Array of changed file paths

**Example:**
```json
{
  "changed_files": [
    "benchmesh-serial-service/src/benchmesh_service/api.py",
    "benchmesh-serial-service/frontend/src/ui/classes/PSU/GenericPSU.tsx"
  ]
}
```

## Usage in Claude Code

Claude Code can now use this MCP service to run tests automatically:

### Example 1: After code changes
```
User: "I just updated the API endpoint, please test it"
Claude: [Uses run_changed_tests with the modified files]
```

### Example 2: Before committing
```
User: "Run all tests before I commit"
Claude: [Uses run_all_tests]
```

### Example 3: Focused testing
```
User: "Test only the serial manager integration"
Claude: [Uses run_integration_tests with appropriate path]
```

## Python Client Helper

For programmatic access, use the client helper:

```python
from mcp_services.testing.client_helper import TestClient

client = TestClient()

# Run backend tests
results = await client.run_backend_tests(verbose=True)

# Run all tests
results = await client.run_all_tests()

# Test changed files
results = await client.run_changed_tests([
    "benchmesh-serial-service/src/benchmesh_service/api.py"
])
```

Or use convenience functions:

```python
from mcp_services.testing.client_helper import test_all, test_backend

# Quick test run
results = await test_all(verbose=True)
results = await test_backend("test_api_instruments.py")
```

## Test Result Format

All tools return results in this format:

```json
{
  "success": true,
  "output": "===== test session starts =====\n...",
  "error": "",
  "returncode": 0,
  "report": {
    "tests": [...],
    "summary": {...}
  }
}
```

## Integration with BenchMesh Workflow

This MCP service integrates with BenchMesh's TDD workflow:

1. **Make code changes**
2. **MCP automatically runs affected tests**
3. **Get immediate feedback**
4. **Fix any failures**
5. **Repeat until all tests pass**

This aligns with the project's requirement:
> "always MUST run tests after the code changes"

## Architecture

```
mcp_services/testing/
├── server.py           # MCP server implementation
├── client_helper.py    # Python client for easy access
├── requirements.txt    # Dependencies
├── config.json        # MCP configuration
└── README.md          # This file
```

## Testing the MCP Service

Run the demo:
```bash
cd /home/marek/project/BenchMesh/mcp_services/testing
python3 client_helper.py
```

## Troubleshooting

### Tests not found
- Ensure you're running from the project root
- Check that test paths are correct

### Permission errors
- Make sure server.py is executable: `chmod +x server.py`

### MCP connection issues
- Verify the path in config.json matches your installation
- Check that all dependencies are installed

## Future Enhancements

Potential additions:
- Coverage tracking over time
- Test performance metrics
- Automatic test generation suggestions
- Parallel test execution
- Test result caching
