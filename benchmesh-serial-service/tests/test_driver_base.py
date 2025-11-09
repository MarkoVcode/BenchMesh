"""
Unit tests for DriverBase abstract class.

Tests cover:
- Abstract method enforcement
- Common implemented methods
- Transport delegation
- Helper methods
- USB TMC auto-detection
- Cache initialization
"""

import pytest
from unittest.mock import Mock, MagicMock
from benchmesh_service.drivers.base import DriverBase
from benchmesh_service.transport import SerialTransport, UsbTmcTransport
from benchmesh_service.cache import SimpleCache


# ===== TEST FIXTURES =====

class ConcreteDriver(DriverBase):
    """Minimal concrete driver for testing."""

    def query_identify(self) -> str:
        return "TEST,DRIVER,SN:12345,V1.0"

    def poll_status(self, channel: int) -> dict:
        return {"STATUS": "OK", "CHANNEL": channel}


class IncompleteDriver(DriverBase):
    """Driver missing required methods (for testing abstract enforcement)."""
    pass


@pytest.fixture
def mock_serial_transport():
    """Mock SerialTransport for testing."""
    transport = Mock(spec=SerialTransport)
    transport.is_open = True
    transport.write = Mock()
    transport.write_line = Mock()
    transport.read = Mock(return_value=b"response")
    transport.read_until_reol = Mock(return_value="response")
    transport.close = Mock()
    return transport


@pytest.fixture
def mock_usbtmc_transport():
    """Mock UsbTmcTransport for testing."""
    transport = Mock(spec=UsbTmcTransport)
    transport.is_open = True
    transport.write_line = Mock()
    transport.read_until_reol = Mock(return_value="response")
    transport.close = Mock()
    return transport


@pytest.fixture
def driver_with_serial(mock_serial_transport):
    """ConcreteDriver with SerialTransport."""
    return ConcreteDriver(transport=mock_serial_transport)


@pytest.fixture
def driver_with_usbtmc(mock_usbtmc_transport):
    """ConcreteDriver with UsbTmcTransport."""
    return ConcreteDriver(transport=mock_usbtmc_transport)


# ===== ABSTRACT METHOD TESTS =====

class TestAbstractMethodEnforcement:
    """Test that abstract methods must be implemented."""

    def test_cannot_instantiate_base_class_directly(self):
        """Test that DriverBase cannot be instantiated directly."""
        mock_transport = Mock()
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DriverBase(transport=mock_transport)

    def test_incomplete_driver_cannot_be_instantiated(self):
        """Test that incomplete driver (missing abstract methods) cannot be instantiated."""
        mock_transport = Mock()
        with pytest.raises(TypeError):
            IncompleteDriver(transport=mock_transport)

    def test_concrete_driver_can_be_instantiated(self, mock_serial_transport):
        """Test that complete driver with all abstract methods can be instantiated."""
        driver = ConcreteDriver(transport=mock_serial_transport)
        assert driver is not None
        assert isinstance(driver, DriverBase)


# ===== INITIALIZATION TESTS =====

class TestDriverInitialization:
    """Test driver initialization."""

    def test_initializes_with_transport(self, mock_serial_transport):
        """Test that driver initializes with provided transport."""
        driver = ConcreteDriver(transport=mock_serial_transport)
        assert driver.t is mock_serial_transport

    def test_initializes_cache(self, driver_with_serial):
        """Test that driver automatically initializes SimpleCache."""
        assert driver_with_serial.cache is not None
        assert isinstance(driver_with_serial.cache, SimpleCache)

    def test_cache_is_independent_per_instance(self, mock_serial_transport):
        """Test that each driver instance gets its own cache."""
        driver1 = ConcreteDriver(transport=mock_serial_transport)
        driver2 = ConcreteDriver(transport=mock_serial_transport)

        driver1.cache.set("key", "value1")
        driver2.cache.set("key", "value2")

        assert driver1.cache.get("key") == "value1"
        assert driver2.cache.get("key") == "value2"


# ===== ABSTRACT METHOD IMPLEMENTATION TESTS =====

class TestAbstractMethodImplementations:
    """Test that concrete implementations of abstract methods work."""

    def test_query_identify(self, driver_with_serial):
        """Test query_identify implementation."""
        result = driver_with_serial.query_identify()
        assert result == "TEST,DRIVER,SN:12345,V1.0"

    def test_poll_status(self, driver_with_serial):
        """Test poll_status implementation."""
        result = driver_with_serial.poll_status(channel=1)
        assert result == {"STATUS": "OK", "CHANNEL": 1}


# ===== COMMON METHOD TESTS =====

class TestCommonMethods:
    """Test common implemented methods from base class."""

    def test_close(self, driver_with_serial, mock_serial_transport):
        """Test close() delegates to transport."""
        driver_with_serial.close()
        mock_serial_transport.close.assert_called_once()

    def test_is_connected_when_open(self, driver_with_serial, mock_serial_transport):
        """Test is_connected() returns True when transport is open."""
        mock_serial_transport.is_open = True
        assert driver_with_serial.is_connected() is True

    def test_is_connected_when_closed(self, driver_with_serial, mock_serial_transport):
        """Test is_connected() returns False when transport is closed."""
        mock_serial_transport.is_open = False
        assert driver_with_serial.is_connected() is False


# ===== SET_RESET TESTS =====

class TestSetReset:
    """Test set_reset() with USB TMC auto-detection."""

    def test_set_reset_with_serial_reads_response(self, driver_with_serial, mock_serial_transport):
        """Test that set_reset() reads response for Serial transports."""
        mock_serial_transport.read_until_reol.return_value = "OK"

        result = driver_with_serial.set_reset()

        mock_serial_transport.write_line.assert_called_once_with('*RST')
        mock_serial_transport.read_until_reol.assert_called_once_with(1024)
        assert result == "OK"

    def test_set_reset_with_usbtmc_no_read(self, driver_with_usbtmc, mock_usbtmc_transport):
        """Test that set_reset() does NOT read response for USB TMC transports."""
        result = driver_with_usbtmc.set_reset()

        mock_usbtmc_transport.write_line.assert_called_once_with('*RST')
        mock_usbtmc_transport.read_until_reol.assert_not_called()
        assert result is None


# ===== TRANSPORT DELEGATION TESTS =====

class TestTransportDelegation:
    """Test that base class methods delegate to transport correctly."""

    def test_write(self, driver_with_serial, mock_serial_transport):
        """Test write() delegates to transport.write()."""
        driver_with_serial.write(b"test data")
        mock_serial_transport.write.assert_called_once_with(b"test data")

    def test_write_line(self, driver_with_serial, mock_serial_transport):
        """Test write_line() delegates to transport.write_line()."""
        driver_with_serial.write_line("*IDN?")
        mock_serial_transport.write_line.assert_called_once_with("*IDN?")

    def test_read(self, driver_with_serial, mock_serial_transport):
        """Test read() delegates to transport.read()."""
        mock_serial_transport.read.return_value = b"data"

        result = driver_with_serial.read(size=512)

        mock_serial_transport.read.assert_called_once_with(512)
        assert result == b"data"

    def test_read_default_size(self, driver_with_serial, mock_serial_transport):
        """Test read() uses default size of 1024."""
        driver_with_serial.read()
        mock_serial_transport.read.assert_called_once_with(1024)

    def test_read_until_reol(self, driver_with_serial, mock_serial_transport):
        """Test read_until_reol() delegates to transport.read_until_reol()."""
        mock_serial_transport.read_until_reol.return_value = "response text"

        result = driver_with_serial.read_until_reol(max_bytes=2048)

        mock_serial_transport.read_until_reol.assert_called_once_with(2048)
        assert result == "response text"


# ===== USB TMC DETECTION TESTS =====

class TestUsbTmcDetection:
    """Test _is_usb_tmc() helper method."""

    def test_is_usb_tmc_with_serial_transport(self, driver_with_serial):
        """Test _is_usb_tmc() returns False for SerialTransport."""
        assert driver_with_serial._is_usb_tmc() is False

    def test_is_usb_tmc_with_usbtmc_transport(self, driver_with_usbtmc):
        """Test _is_usb_tmc() returns True for UsbTmcTransport."""
        assert driver_with_usbtmc._is_usb_tmc() is True


# ===== HELPER METHOD TESTS =====

class TestParseNumeric:
    """Test _parse_numeric() helper method."""

    def test_parse_numeric_from_string(self, driver_with_serial):
        """Test parsing numeric from string."""
        assert driver_with_serial._parse_numeric("5.0") == 5.0
        assert driver_with_serial._parse_numeric("42") == 42.0
        assert driver_with_serial._parse_numeric("  3.14  ") == 3.14

    def test_parse_numeric_from_bytes(self, driver_with_serial):
        """Test parsing numeric from bytes."""
        assert driver_with_serial._parse_numeric(b"5.0V") == 5.0
        assert driver_with_serial._parse_numeric(b"42A") == 42.0

    def test_parse_numeric_scientific_notation(self, driver_with_serial):
        """Test parsing scientific notation."""
        assert driver_with_serial._parse_numeric("1.23E-4") == 0.000123
        assert driver_with_serial._parse_numeric("5.67e+2") == 567.0
        assert driver_with_serial._parse_numeric("1E3") == 1000.0

    def test_parse_numeric_with_units(self, driver_with_serial):
        """Test parsing numbers with units (extracts first number)."""
        assert driver_with_serial._parse_numeric("5.0V") == 5.0
        assert driver_with_serial._parse_numeric("2.5A") == 2.5
        assert driver_with_serial._parse_numeric("100mV") == 100.0

    def test_parse_numeric_negative_numbers(self, driver_with_serial):
        """Test parsing negative numbers."""
        assert driver_with_serial._parse_numeric("-5.0") == -5.0
        assert driver_with_serial._parse_numeric("-1.23E-4") == -0.000123

    def test_parse_numeric_none_input(self, driver_with_serial):
        """Test parsing None returns None."""
        assert driver_with_serial._parse_numeric(None) is None

    def test_parse_numeric_no_number(self, driver_with_serial):
        """Test parsing string with no number returns None."""
        assert driver_with_serial._parse_numeric("ERROR") is None
        assert driver_with_serial._parse_numeric("   ") is None


class TestCleanResponse:
    """Test _clean_response() helper method."""

    def test_clean_response_from_string(self, driver_with_serial):
        """Test cleaning string response."""
        assert driver_with_serial._clean_response("  hello  ") == "hello"
        assert driver_with_serial._clean_response("test") == "test"

    def test_clean_response_from_bytes(self, driver_with_serial):
        """Test cleaning bytes response."""
        assert driver_with_serial._clean_response(b"  hello  ") == "hello"
        assert driver_with_serial._clean_response(b"test") == "test"

    def test_clean_response_removes_quotes(self, driver_with_serial):
        """Test that surrounding quotes are removed."""
        assert driver_with_serial._clean_response('"quoted"') == "quoted"
        assert driver_with_serial._clean_response("'quoted'") == "quoted"
        assert driver_with_serial._clean_response('  "quoted"  ') == "quoted"

    def test_clean_response_keeps_inner_quotes(self, driver_with_serial):
        """Test that inner quotes are preserved."""
        assert driver_with_serial._clean_response('"hello "world""') == 'hello "world"'

    def test_clean_response_none_input(self, driver_with_serial):
        """Test cleaning None returns empty string."""
        assert driver_with_serial._clean_response(None) == ""

    def test_clean_response_utf8_fallback_latin1(self, driver_with_serial):
        """Test UTF-8 with Latin-1 fallback for bytes."""
        # Valid UTF-8
        assert driver_with_serial._clean_response(b"hello") == "hello"

        # Invalid UTF-8 bytes (should fallback to Latin-1)
        invalid_utf8 = b"\xff\xfe"
        result = driver_with_serial._clean_response(invalid_utf8)
        assert result != ""  # Should decode as Latin-1


# ===== CACHE INTEGRATION TESTS =====

class TestCacheIntegration:
    """Test that cache works correctly with drivers."""

    def test_cache_available_to_driver_methods(self, driver_with_serial):
        """Test that driver methods can use self.cache."""
        # Simulate caching in a driver method
        driver_with_serial.cache.set("voltage", 5.0)
        assert driver_with_serial.cache.get("voltage") == 5.0

    def test_cache_get_or_set_pattern(self, driver_with_serial):
        """Test get_or_set pattern commonly used in drivers."""
        call_count = [0]

        def expensive_query():
            call_count[0] += 1
            return "computed_value"

        # First call - computes
        result1 = driver_with_serial.cache.get_or_set("key", expensive_query)
        assert result1 == "computed_value"
        assert call_count[0] == 1

        # Second call - cached
        result2 = driver_with_serial.cache.get_or_set("key", expensive_query)
        assert result2 == "computed_value"
        assert call_count[0] == 1  # Not called again


# ===== POLL_MULTI_CLASS HELPER TESTS =====

class TestPollMultiClass:
    """Test _poll_multi_class() helper method for multi-class devices."""

    @pytest.fixture
    def multi_class_driver(self, mock_serial_transport):
        """ConcreteDriver with mock methods for multi-class polling."""

        class MultiClassDriver(ConcreteDriver):
            def __init__(self, transport):
                super().__init__(transport)
                self.psu_poll_called = False
                self.dmm_poll_called = False

            def poll_status_psu(self, channel: int):
                self.psu_poll_called = True
                return {"VOUT": 12.5, "IOUT": 1.2}

            def poll_status_dmm(self, channel: int):
                self.dmm_poll_called = True
                return {"MEAS": 3.14, "MODE": "VOLT"}

        return MultiClassDriver(transport=mock_serial_transport)

    def test_both_classes_succeed(self, multi_class_driver):
        """Test _poll_multi_class when both classes succeed."""
        result = multi_class_driver._poll_multi_class(1, {
            "PSU": multi_class_driver.poll_status_psu,
            "DMM": multi_class_driver.poll_status_dmm
        })

        assert result == {
            "PSU": {"VOUT": 12.5, "IOUT": 1.2},
            "DMM": {"MEAS": 3.14, "MODE": "VOLT"}
        }
        assert multi_class_driver.psu_poll_called
        assert multi_class_driver.dmm_poll_called

    def test_partial_success_psu_succeeds_dmm_fails(self, multi_class_driver):
        """Test partial success - PSU succeeds, DMM fails."""

        def failing_dmm_poll(channel):
            raise TimeoutError("DMM timed out")

        result = multi_class_driver._poll_multi_class(1, {
            "PSU": multi_class_driver.poll_status_psu,
            "DMM": failing_dmm_poll
        })

        # Should return partial data
        assert result == {
            "PSU": {"VOUT": 12.5, "IOUT": 1.2},
            "DMM": None
        }

    def test_partial_success_psu_fails_dmm_succeeds(self, multi_class_driver):
        """Test partial success - PSU fails, DMM succeeds."""

        def failing_psu_poll(channel):
            raise RuntimeError("PSU communication error")

        result = multi_class_driver._poll_multi_class(1, {
            "PSU": failing_psu_poll,
            "DMM": multi_class_driver.poll_status_dmm
        })

        # Should return partial data
        assert result == {
            "PSU": None,
            "DMM": {"MEAS": 3.14, "MODE": "VOLT"}
        }

    def test_all_classes_fail_raises_exception(self, multi_class_driver):
        """Test that all classes failing raises RuntimeError."""

        def failing_psu_poll(channel):
            raise TimeoutError("PSU timed out")

        def failing_dmm_poll(channel):
            raise TimeoutError("DMM timed out")

        with pytest.raises(RuntimeError, match="All classes .* failed to poll"):
            multi_class_driver._poll_multi_class(1, {
                "PSU": failing_psu_poll,
                "DMM": failing_dmm_poll
            })

    def test_empty_dict_response_treated_as_failure(self, multi_class_driver):
        """Test that empty dict {} response is treated as failure."""

        def empty_psu_poll(channel):
            return {}  # Device off

        result = multi_class_driver._poll_multi_class(1, {
            "PSU": empty_psu_poll,
            "DMM": multi_class_driver.poll_status_dmm
        })

        # PSU returned empty dict, DMM succeeded
        assert result == {
            "PSU": None,
            "DMM": {"MEAS": 3.14, "MODE": "VOLT"}
        }

    def test_all_empty_dicts_raises_exception(self, multi_class_driver):
        """Test that all classes returning empty dict raises RuntimeError."""

        def empty_psu_poll(channel):
            return {}

        def empty_dmm_poll(channel):
            return {}

        with pytest.raises(RuntimeError, match="All classes .* failed to poll"):
            multi_class_driver._poll_multi_class(1, {
                "PSU": empty_psu_poll,
                "DMM": empty_dmm_poll
            })

    def test_mixed_failure_types(self, multi_class_driver):
        """Test mixed failure types (exception + empty dict)."""

        def empty_psu_poll(channel):
            return {}  # Device off

        def failing_dmm_poll(channel):
            raise TimeoutError("DMM timeout")

        def ok_oel_poll(channel):
            return {"VIN": 5.0, "IIN": 2.0}

        result = multi_class_driver._poll_multi_class(1, {
            "PSU": empty_psu_poll,
            "DMM": failing_dmm_poll,
            "OEL": ok_oel_poll
        })

        # Only OEL succeeded
        assert result == {
            "PSU": None,
            "DMM": None,
            "OEL": {"VIN": 5.0, "IIN": 2.0}
        }

    def test_channel_parameter_passed_to_poll_methods(self, mock_serial_transport):
        """Test that channel parameter is correctly passed to poll methods."""
        channel_received = [None, None]

        class ChannelTestDriver(ConcreteDriver):
            def poll_status_psu(self, channel: int):
                channel_received[0] = channel
                return {"VOUT": 12.5}

            def poll_status_dmm(self, channel: int):
                channel_received[1] = channel
                return {"MEAS": 3.14}

        driver = ChannelTestDriver(transport=mock_serial_transport)

        driver._poll_multi_class(2, {
            "PSU": driver.poll_status_psu,
            "DMM": driver.poll_status_dmm
        })

        assert channel_received[0] == 2
        assert channel_received[1] == 2

    def test_single_class_device_success(self, multi_class_driver):
        """Test _poll_multi_class with single class (edge case)."""
        result = multi_class_driver._poll_multi_class(1, {
            "PSU": multi_class_driver.poll_status_psu
        })

        assert result == {
            "PSU": {"VOUT": 12.5, "IOUT": 1.2}
        }

    def test_single_class_device_failure(self, multi_class_driver):
        """Test _poll_multi_class with single class failing."""

        def failing_poll(channel):
            raise TimeoutError("Timeout")

        with pytest.raises(RuntimeError, match="All classes .* failed to poll"):
            multi_class_driver._poll_multi_class(1, {
                "PSU": failing_poll
            })
