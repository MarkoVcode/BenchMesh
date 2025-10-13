"""
Test API method name resolution.

This test ensures that the API correctly resolves partial method names to full
driver method names based on HTTP verb (GET -> query_, POST -> set_).
"""
import os
import sys
from unittest.mock import Mock
import pytest

THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fastapi import HTTPException
from benchmesh_service.api import _resolve_method_name


class FakeDriver:
    """Fake driver with some query_ and set_ methods."""
    def query_voltage(self, channel: int):
        return "12.0V"

    def query_current(self, channel: int):
        return "1.5A"

    def set_voltage(self, channel: int, value: float):
        pass

    def set_current(self, channel: int, value: float):
        pass

    def set_output(self, channel: int, value: str):
        pass

    def poll_status(self, channel: int):
        """Method without prefix."""
        return {"status": "ok"}


def test_get_resolves_to_query_prefix():
    """Test that GET requests resolve partial names to query_ prefix."""
    driver = FakeDriver()

    # "voltage" should resolve to "query_voltage"
    resolved = _resolve_method_name(driver, "voltage", "GET")
    assert resolved == "query_voltage"

    # "current" should resolve to "query_current"
    resolved = _resolve_method_name(driver, "current", "GET")
    assert resolved == "query_current"


def test_post_resolves_to_set_prefix():
    """Test that POST requests resolve partial names to set_ prefix."""
    driver = FakeDriver()

    # "voltage" should resolve to "set_voltage"
    resolved = _resolve_method_name(driver, "voltage", "POST")
    assert resolved == "set_voltage"

    # "current" should resolve to "set_current"
    resolved = _resolve_method_name(driver, "current", "POST")
    assert resolved == "set_current"

    # "output" should resolve to "set_output"
    resolved = _resolve_method_name(driver, "output", "POST")
    assert resolved == "set_output"


def test_no_arbitrary_method_execution():
    """Test that arbitrary method names are rejected (security)."""
    driver = FakeDriver()

    # Trying to call poll_status directly should fail
    with pytest.raises(HTTPException) as exc_info:
        _resolve_method_name(driver, "poll_status", "GET")
    assert exc_info.value.status_code == 400
    assert "query_poll_status" in exc_info.value.detail

    # Trying to call private methods should fail
    driver._private_method = Mock()
    with pytest.raises(HTTPException) as exc_info:
        _resolve_method_name(driver, "_private_method", "POST")
    assert exc_info.value.status_code == 400

    # Trying to call __init__ or other special methods should fail
    with pytest.raises(HTTPException) as exc_info:
        _resolve_method_name(driver, "__init__", "POST")
    assert exc_info.value.status_code == 400


def test_nonexistent_method_raises_error():
    """Test that requesting a nonexistent method raises HTTPException."""
    driver = FakeDriver()

    # Requesting "power" which doesn't exist should raise error
    with pytest.raises(HTTPException) as exc_info:
        _resolve_method_name(driver, "power", "GET")

    assert exc_info.value.status_code == 400
    assert "query_power" in exc_info.value.detail
    assert "not found" in exc_info.value.detail.lower()

    # Same for POST
    with pytest.raises(HTTPException) as exc_info:
        _resolve_method_name(driver, "power", "POST")

    assert exc_info.value.status_code == 400
    assert "set_power" in exc_info.value.detail
    assert "not found" in exc_info.value.detail.lower()


def test_non_callable_attribute_raises_error():
    """Test that non-callable attributes don't resolve as methods."""
    driver = FakeDriver()
    driver.voltage_value = "12.0V"  # Not a method, just an attribute

    with pytest.raises(HTTPException) as exc_info:
        _resolve_method_name(driver, "voltage_value", "GET")

    assert exc_info.value.status_code == 400


def test_only_prefixed_methods_allowed():
    """Test that only properly prefixed methods are allowed (security)."""
    driver = FakeDriver()

    # Add a non-prefixed "temperature" method (no query_ or set_ prefix)
    driver.temperature = Mock(return_value="25.0C")

    # Should fail because query_temperature doesn't exist (only temperature exists)
    # This prevents calling arbitrary methods that don't follow the convention
    with pytest.raises(HTTPException) as exc_info:
        _resolve_method_name(driver, "temperature", "GET")
    assert exc_info.value.status_code == 400
    assert "query_temperature" in exc_info.value.detail

    # Should fail for POST too (set_temperature doesn't exist)
    with pytest.raises(HTTPException) as exc_info:
        _resolve_method_name(driver, "temperature", "POST")
    assert exc_info.value.status_code == 400
    assert "set_temperature" in exc_info.value.detail

    # Verify that properly prefixed methods still work
    resolved = _resolve_method_name(driver, "voltage", "GET")
    assert resolved == "query_voltage"

    resolved = _resolve_method_name(driver, "voltage", "POST")
    assert resolved == "set_voltage"


def test_case_sensitivity():
    """Test that method resolution is case-sensitive."""
    driver = FakeDriver()

    # "Voltage" (capital V) should not resolve to query_voltage
    with pytest.raises(HTTPException):
        _resolve_method_name(driver, "Voltage", "GET")

    # "VOLTAGE" should not resolve to query_voltage
    with pytest.raises(HTTPException):
        _resolve_method_name(driver, "VOLTAGE", "GET")
