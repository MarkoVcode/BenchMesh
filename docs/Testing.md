# Testing Guide

This guide covers testing strategies, running tests, writing tests, and using BenchMesh's MCP testing service.

## Table of Contents

- [Overview](#overview)
- [Test Types](#test-types)
- [Running Tests](#running-tests)
- [MCP Testing Service](#mcp-testing-service)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)

## Overview

BenchMesh follows Test-Driven Development (TDD) principles with comprehensive test coverage across:
- **Backend**: Python pytest tests for serial service
- **Frontend**: Vitest tests for React components
- **Integration**: End-to-end tests with real devices
- **MCP Service**: Automated test execution through Claude Code

### Test Philosophy

From CLAUDE.md:
> - Apply TDD principles when adding new features
> - Always MUST run tests after code changes
> - Always MUST cover new development with tests - whatever is added or improved
> - Differentiate between unit tests and integration tests
> - Integration tests should NOT run in GitHub Actions (reserve for local/staging testing only)
> - All new unit tests suitable for GitHub Actions must be automatically added to the CI workflow

## Test Types

### Unit Tests

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast execution (< 1 second per test)
- No external dependencies (mock serial, HTTP, etc.)
- Deterministic results
- Run in CI/CD pipelines

**Location**:
- Backend: `benchmesh-serial-service/tests/`
- Frontend: `benchmesh-serial-service/frontend/src/**/*.test.tsx`

### Integration Tests

**Purpose**: Test component interactions with real dependencies

**Characteristics**:
- Require physical hardware
- Slower execution
- May have environmental dependencies
- Run locally or in staging only

**Marking**: Use `@pytest.mark.integration` decorator

```python
import pytest

@pytest.mark.integration
def test_real_device_connection():
    """Test connection to actual hardware."""
    # This test requires real device on /dev/ttyUSB0
    pass
```

### End-to-End Tests

**Purpose**: Test complete user workflows

**Location**: `test_automation_ui.sh`, `/RESTART_AND_TEST.sh`

**Characteristics**:
- Tests full stack (backend + frontend)
- Browser automation
- Real device interactions

## Running Tests

### Backend Tests

```bash
# Run all unit tests
pytest benchmesh-serial-service/tests

# Run with verbose output
pytest -v benchmesh-serial-service/tests

# Run specific test file
pytest benchmesh-serial-service/tests/test_serial_manager.py

# Run specific test function
pytest benchmesh-serial-service/tests/test_serial_manager.py::test_start

# Run with coverage
pytest --cov=benchmesh_service benchmesh-serial-service/tests

# Generate HTML coverage report
pytest --cov=benchmesh_service --cov-report=html benchmesh-serial-service/tests
# Open htmlcov/index.html
```

### Frontend Tests

```bash
cd benchmesh-serial-service/frontend

# Run tests once
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- src/components/Dashboard.test.tsx
```

### Integration Tests

```bash
# Run integration tests only (requires hardware)
pytest -m integration benchmesh-serial-service/tests

# Run with specific device
pytest -m integration benchmesh-serial-service/tests \
    --device-port=/dev/ttyUSB0
```

### All Tests

```bash
# Backend tests
python3 -m pytest benchmesh-serial-service/tests

# Frontend tests
cd benchmesh-serial-service/frontend && npm run test:run

# Or use the MCP service (see below)
```

## MCP Testing Service

BenchMesh includes a Model Context Protocol (MCP) service for automated test execution through Claude Code.

### Quick Start

```bash
# Install MCP service dependencies
cd mcp_services/testing
pip install -r requirements.txt --user

# Test the service
cd /home/marek/project/BenchMesh
python3 mcp_services/testing/client_helper.py
```

### Available MCP Tools

The MCP service provides 7 test tools:

1. **`run_backend_tests`** - Run pytest tests with filtering
2. **`run_frontend_tests`** - Run vitest tests
3. **`run_integration_tests`** - Run integration tests only
4. **`run_electron_tests`** - Run Electron app tests
5. **`run_all_tests`** - Run complete test suite
6. **`discover_tests`** - List all available tests
7. **`run_changed_tests`** - Test only changed files

### Using from Claude Code

The MCP service is automatically available in Claude Code. Ask Claude to:

```
"Run all backend tests"
"Test the serial manager"
"Run tests for changed files"
"Discover all available tests"
```

Claude will use the appropriate MCP tool and provide structured results.

### Programmatic Usage

```python
from mcp_services.testing.client_helper import test_all, test_backend, test_changed

# Run all tests
results = await test_all(verbose=True)

# Run specific backend tests
results = await test_backend("test_serial_manager.py", verbose=True)

# Test changed files
results = await test_changed([
    "benchmesh-serial-service/src/benchmesh_service/api.py"
])

# Parse results
if results["status"] == "success":
    print(f"✓ Passed: {results['passed']}/{results['total']}")
else:
    print(f"✗ Failed: {results['failed']}/{results['total']}")
    for failure in results.get("failures", []):
        print(f"  - {failure['test']}: {failure['message']}")
```

### Test Metrics

The MCP service returns structured JSON with:

```json
{
  "status": "success|failure",
  "total": 46,
  "passed": 45,
  "failed": 1,
  "skipped": 0,
  "duration": 12.34,
  "failures": [
    {
      "test": "test_serial_manager::test_reconnect",
      "file": "tests/test_serial_manager.py",
      "line": 123,
      "message": "AssertionError: Expected 2, got 1"
    }
  ]
}
```

## Writing Tests

### Backend Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from benchmesh_service.serial_manager import SerialManager

@pytest.fixture
def mock_config():
    """Provide test configuration."""
    return {
        "version": 1,
        "devices": [
            {
                "id": "test-psu",
                "driver": "tenma_72",
                "port": "/dev/ttyUSB0",
                "baud": 9600
            }
        ]
    }

@pytest.fixture
def mock_transport():
    """Mock serial transport."""
    transport = Mock()
    transport.open.return_value = transport
    transport.read_until_reol.return_value = "TENMA 72-2540 V2.1"
    return transport

def test_serial_manager_initialization(mock_config):
    """Test SerialManager initialization."""
    manager = SerialManager(mock_config)
    assert manager is not None
    assert len(manager.devices) == 1

def test_device_connection(mock_config, mock_transport, monkeypatch):
    """Test device connection."""
    def mock_serial(*args, **kwargs):
        return mock_transport

    monkeypatch.setattr('benchmesh_service.transport.SerialTransport', mock_serial)

    manager = SerialManager(mock_config)
    manager.start()

    # Verify device connected
    assert "test-psu" in manager.connections
    mock_transport.open.assert_called_once()
```

### Frontend Test Structure

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Dashboard from './Dashboard';

describe('Dashboard Component', () => {
  it('renders device list', () => {
    const devices = [
      { id: 'psu-1', name: 'TENMA PSU', status: 'connected' }
    ];

    render(<Dashboard devices={devices} />);

    expect(screen.getByText('TENMA PSU')).toBeInTheDocument();
    expect(screen.getByText('connected')).toBeInTheDocument();
  });

  it('calls onDeviceSelect when device clicked', () => {
    const handleSelect = vi.fn();
    const devices = [
      { id: 'psu-1', name: 'TENMA PSU', status: 'connected' }
    ];

    render(<Dashboard devices={devices} onDeviceSelect={handleSelect} />);

    const deviceCard = screen.getByText('TENMA PSU');
    fireEvent.click(deviceCard);

    expect(handleSelect).toHaveBeenCalledWith('psu-1');
  });

  it('displays loading state', () => {
    render(<Dashboard devices={[]} loading={true} />);

    expect(screen.getByText('Loading devices...')).toBeInTheDocument();
  });
});
```

### Integration Test Example

```python
import pytest
from benchmesh_service.drivers.tenma_72.driver import TenmaPSU

@pytest.mark.integration
def test_tenma_psu_real_device():
    """Test with actual TENMA PSU hardware."""
    # This test requires:
    # - TENMA 72-2540 connected to /dev/ttyUSB0
    # - Device powered on

    driver = TenmaPSU(port='/dev/ttyUSB0', baudrate=9600)

    # Test identification
    idn = driver.query_identify()
    assert "TENMA" in idn
    assert "72-2540" in idn

    # Test voltage query
    voltage = driver.query_voltage(1)
    assert voltage is not None
    assert 0 <= float(voltage) <= 30.0

    # Test setting voltage
    driver.set_voltage(1, 12.0)
    set_voltage = driver.query_voltage(1)
    assert abs(float(set_voltage) - 12.0) < 0.1

    # Cleanup
    driver.set_output(1, False)
```

### Test Fixtures

Create reusable fixtures in `conftest.py`:

```python
# benchmesh-serial-service/tests/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_serial_transport():
    """Provide mocked SerialTransport."""
    transport = Mock()
    transport.open.return_value = transport
    transport.read_until_reol.return_value = "OK"
    return transport

@pytest.fixture
def sample_device_config():
    """Provide sample device configuration."""
    return {
        "id": "test-device",
        "driver": "test_driver",
        "port": "/dev/ttyUSB0",
        "baud": 9600,
        "serial": "8N1"
    }

@pytest.fixture(scope="session")
def real_device_port():
    """Provide real device port for integration tests."""
    import os
    return os.environ.get("TEST_DEVICE_PORT", "/dev/ttyUSB0")
```

## Test Coverage

### Viewing Coverage

```bash
# Backend coverage
pytest --cov=benchmesh_service --cov-report=html benchmesh-serial-service/tests
open htmlcov/index.html

# Frontend coverage
cd benchmesh-serial-service/frontend
npm run test:coverage
open coverage/index.html
```

### Coverage Goals

- **Overall**: > 80%
- **Critical paths**: 100% (SerialManager, API endpoints, drivers)
- **UI components**: > 70%
- **Utilities**: > 90%

### Coverage Reports

Coverage is tracked per module:

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
api.py                          156      8    95%
serial_manager.py               234     12    95%
drivers/tenma_72/driver.py      145     18    88%
transport.py                     87      5    94%
-------------------------------------------------
TOTAL                           622     43    93%
```

## CI/CD Integration

### GitHub Actions Workflow

`.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r benchmesh-serial-service/requirements.txt
          pip install pytest pytest-cov

      - name: Run backend tests
        run: pytest benchmesh-serial-service/tests

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        working-directory: benchmesh-serial-service/frontend
        run: npm ci

      - name: Run frontend tests
        working-directory: benchmesh-serial-service/frontend
        run: npm run test:run
```

### Skipping Integration Tests in CI

Integration tests are skipped by default (no `-m integration` flag).

To run integration tests in CI (if you have hardware available):

```yaml
- name: Run integration tests
  if: ${{ github.ref == 'refs/heads/staging' }}
  run: pytest -m integration benchmesh-serial-service/tests
```

## Best Practices

### 1. Test Naming

```python
# GOOD - Descriptive names
def test_serial_manager_reconnects_after_device_disconnect():
    pass

def test_api_endpoint_returns_404_for_unknown_device():
    pass

# BAD - Vague names
def test_manager():
    pass

def test_api():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_set_voltage():
    # Arrange - Set up test conditions
    driver = TenmaPSU(port='/dev/ttyUSB0')
    expected_voltage = 12.0

    # Act - Perform the action
    driver.set_voltage(1, expected_voltage)

    # Assert - Verify the result
    actual_voltage = driver.query_voltage(1)
    assert abs(actual_voltage - expected_voltage) < 0.1
```

### 3. Mock External Dependencies

```python
# GOOD - Mock serial communication
@patch('benchmesh_service.transport.Serial')
def test_driver_communication(mock_serial):
    mock_serial.return_value.readline.return_value = b"12.0\r\n"

    driver = TenmaPSU(port='/dev/ttyUSB0')
    voltage = driver.query_voltage(1)

    assert voltage == "12.0"

# BAD - Require real hardware for unit tests
def test_driver_communication():
    driver = TenmaPSU(port='/dev/ttyUSB0')  # Fails if no device
    voltage = driver.query_voltage(1)
    assert voltage is not None
```

### 4. Test One Thing

```python
# GOOD - Single responsibility
def test_device_connects_successfully():
    manager = SerialManager(config)
    manager.connect_device('psu-1')
    assert manager.is_connected('psu-1')

def test_device_appears_in_registry_after_connection():
    manager = SerialManager(config)
    manager.connect_device('psu-1')
    assert 'psu-1' in manager.registry

# BAD - Testing multiple things
def test_device_connection():
    manager = SerialManager(config)
    manager.connect_device('psu-1')
    assert manager.is_connected('psu-1')
    assert 'psu-1' in manager.registry
    assert manager.get_device_status('psu-1') is not None
    # Too much in one test
```

### 5. Use Parametrize for Similar Tests

```python
@pytest.mark.parametrize("voltage,expected", [
    (0.0, 0.0),
    (12.0, 12.0),
    (30.0, 30.0),
])
def test_set_voltage_various_values(voltage, expected):
    driver = TenmaPSU(port='/dev/ttyUSB0')
    driver.set_voltage(1, voltage)
    actual = driver.query_voltage(1)
    assert abs(actual - expected) < 0.1
```

### 6. Clean Up Resources

```python
@pytest.fixture
def driver():
    """Create driver instance."""
    d = TenmaPSU(port='/dev/ttyUSB0')
    yield d
    # Cleanup after test
    d.set_output(1, False)
    d.close()
```

### 7. Document Test Intent

```python
def test_device_reconnects_after_transient_failure():
    """
    Verify that SerialManager automatically reconnects when a device
    experiences a transient communication failure.

    This is critical for handling unstable USB connections or device
    power cycles during long-running experiments.
    """
    # Test implementation...
```

## Troubleshooting Tests

### Tests Hanging

```bash
# Run with timeout
pytest --timeout=10 benchmesh-serial-service/tests

# Or use asyncio timeout for async tests
@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_async_operation():
    await some_operation()
```

### Import Errors

```bash
# Set PYTHONPATH
export PYTHONPATH=benchmesh-serial-service/src
pytest benchmesh-serial-service/tests

# Or install in editable mode
pip install -e benchmesh-serial-service
```

### Serial Port Conflicts

```python
# Ensure tests clean up ports
@pytest.fixture
def serial_port():
    port = SerialTransport('/dev/ttyUSB0', 9600)
    port.open()
    yield port
    port.close()  # Critical!
```

### Flaky Tests

```python
# Add retries for flaky integration tests
@pytest.mark.flaky(reruns=3, reruns_delay=2)
@pytest.mark.integration
def test_device_connection_with_retry():
    # Sometimes hardware needs warm-up
    driver = TenmaPSU(port='/dev/ttyUSB0')
    assert driver.query_identify() is not None
```

## Related Documentation

- [Driver Development](Driver-Development) - Writing driver tests
- [Contributing](../CONTRIBUTING.md) - Contribution guidelines
- [Architecture](Architecture) - System design
- [MCP Service README](../mcp_services/testing/README.md) - MCP testing details
