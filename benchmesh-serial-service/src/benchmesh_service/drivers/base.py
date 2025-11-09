"""
Base class for all instrument drivers.

Provides common initialization, transport delegation, caching, and helper methods
that all drivers need. Concrete drivers inherit and implement device-specific
SCPI commands and polling logic.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..cache import SimpleCache
from ..transport import Transport, UsbTmcTransport


class DriverBase(ABC):
    """
    Abstract base class for all instrument drivers.

    All drivers must inherit from this class and implement the required abstract methods.
    The base class provides:
    - Transport management and delegation
    - Built-in caching for all drivers
    - Common helper methods for parsing responses
    - Automatic USB TMC detection for set commands

    Example:
        from ..base import DriverBase

        class MyDriver(DriverBase):
            def query_identify(self) -> str:
                self.t.write_line('*IDN?')
                return self.t.read_until_reol(1024)

            def poll_status(self, channel: int) -> dict:
                voltage = self.cache.get_or_set("voltage", self.query_voltage, channel)
                return {"VOLTAGE": voltage}

            def query_voltage(self, channel: int) -> str:
                self.t.write_line(f'MEAS:VOLT? CH{channel}')
                return self.t.read_until_reol(1024)
    """

    def __init__(self, transport: Transport):
        """
        Initialize driver with transport.

        Args:
            transport: Configured transport instance (Serial, USB TMC, TCP/IP)
        """
        self.t = transport
        self.cache = SimpleCache()  # All drivers get automatic caching

    # ===== REQUIRED ABSTRACT METHODS =====
    @abstractmethod
    def poll_status(self, channel: int) -> Dict[str, Any]:
        """
        Poll device status for periodic updates.

        Must be implemented by all drivers.
        Called periodically by polling worker thread (every 2-3 seconds typically).

        **RETURN VALUE CONTRACT:**

        - **Success**: Return dictionary with status data
        - **Device off/not responding**: Return empty dict {}
        - **Communication error**: Raise exception (TimeoutError, SerialException, etc.)

        **IMPORTANT - Connection Monitoring:**

        This method serves dual purposes:
        1. **Data collection**: Returns device measurements/status
        2. **Health monitoring**: Signals connection health to worker

        The worker uses the return value to determine connection health:
        - Non-empty dict → Connection healthy, data recorded
        - Empty dict {} → Device not responding, connection dropped
        - Exception raised → Communication failure, connection dropped

        **DO NOT:**
        - ❌ Catch exceptions and return fake data (defeats health monitoring)
        - ❌ Return {"VOUT": None, "IOUT": None} on timeout
        - ❌ Return {"ERROR": str(e)} on exception
        - ❌ Return None instead of {} or raising

        **DO:**
        - ✅ Let transport exceptions propagate naturally
        - ✅ Return empty dict {} only for valid "device off" states
        - ✅ Return meaningful data for standby/off states when possible

        **Examples:**

        CORRECT - Let exceptions propagate (tenma_72 pattern):
            def poll_status(self, channel: int):
                # No try/except - transport errors bubble up
                v = self.query_voltage(channel)  # May raise TimeoutError
                i = self.query_current(channel)  # May raise TimeoutError
                return {"VOUT": v, "IOUT": i}

        CORRECT - Empty dict for device powered off:
            def poll_status(self, channel: int):
                raw = self.query_status(channel)
                if not raw or raw.strip() == "":
                    return {}  # Device powered off, no data available
                return self._parse_status(raw)

        CORRECT - Standby state returns valid data:
            def poll_status(self, channel: int):
                v = self.query_voltage(channel)
                i = self.query_current(channel)
                output_on = self.query_output_state(channel)
                return {
                    "VOUT": v,
                    "IOUT": i,
                    "OUTPUT": "ON" if output_on else "OFF",
                    "SBY": not output_on  # Standby flag
                }

        WRONG - Fake data on communication error:
            def poll_status(self, channel: int):
                try:
                    v = self.query_voltage(channel)
                except TimeoutError:
                    return {"VOUT": None}  # ❌ WRONG! Worker thinks success!

        WRONG - Catching and hiding errors:
            def poll_status(self, channel: int):
                try:
                    return {"DATA": self.query_data(channel)}
                except Exception as e:
                    return {"ERROR": str(e)}  # ❌ WRONG! Truthy dict!

        **Multi-Class Devices:**

        Use _poll_multi_class() helper for devices with multiple classes:

            def poll_status(self, channel: int):
                return self._poll_multi_class(channel, {
                    "PSU": self.poll_status_psu,
                    "DMM": self.poll_status_dmm
                })

        The helper handles partial success gracefully (some classes succeed, some fail).

        Args:
            channel: Channel number (1-based, may be ignored for single-channel devices)

        Returns:
            Dictionary with device status. Keys depend on device type/class.
            For multi-class devices (e.g., OWONSPM), return nested dict:
                {"PSU": {...}, "DMM": {...}}
            Empty dict {} if device powered off or not responding.

        Raises:
            TimeoutError: Serial read timeout (device not responding to query)
            SerialException: Physical connection error (cable disconnected, port closed)
            ValueError: Invalid/unparseable response from device

            Exceptions are caught by worker and trigger health monitoring + reconnection.

        See Also:
            - tenma_72 driver for reference implementation
            - _poll_multi_class() helper for multi-class devices
        """
        pass

    # ===== COMMON IMPLEMENTED METHODS =====   
    def set_reset(self) -> Optional[str]:
        """
        Reset device to factory defaults (*RST command).

        Automatically detects USB TMC devices and skips reading response
        (USB TMC devices don't respond to SET commands).

        For Serial devices, reads and returns response.

        Override this method if device has non-standard reset behavior.

        Returns:
            Response from device (Serial) or None (USB TMC)
        """
        self.t.write_line('*RST')

        # USB TMC devices don't respond to SET commands
        if self._is_usb_tmc():
            return None

        return self.t.read_until_reol(1024)

    def query_identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def query_cache_stats(self):
        return self.cache.get_stats()

    def close(self) -> None:
        """
        Close transport and cleanup resources.

        Override if additional cleanup needed (flush buffers, invalidate cache, etc.)
        """
        self.t.close()

    def is_connected(self) -> bool:
        """
        Check if transport is connected and ready.

        Returns:
            True if transport is open, False otherwise
        """
        return self.t.is_open

    def _poll_multi_class(
        self,
        channel: int,
        poll_methods: Dict[str, callable]
    ) -> Dict[str, Any]:
        """
        Helper for multi-class devices with partial success support.

        Simplifies polling for devices that combine multiple instrument classes
        (e.g., OWON SPM has both PSU and DMM functionality).

        Attempts to poll each class independently. If at least one class
        succeeds, returns partial data with successful classes. If ALL classes
        fail, raises exception to trigger connection drop and reconnection.

        This allows graceful degradation - if DMM fails but PSU works, PSU data
        is still usable while DMM reconnection is attempted.

        Args:
            channel: Channel number to pass to poll methods
            poll_methods: Dict mapping class name to poll method callable
                         e.g., {"PSU": self.poll_status_psu, "DMM": self.poll_status_dmm}

        Returns:
            Dict with class-keyed data. Successful classes have data,
            failed classes have None value.

        Raises:
            RuntimeError: If all classes failed to poll (device completely unresponsive)

        Example:
            def poll_status(self, channel: int):
                return self._poll_multi_class(channel, {
                    "PSU": self.poll_status_psu,
                    "DMM": self.poll_status_dmm
                })

        Example output (partial success):
            {
                "PSU": {"VOUT": 12.5, "IOUT": 1.2},  # Success
                "DMM": None                            # Failed
            }

        Example behavior:
            - If PSU and DMM both succeed: Returns both data dicts
            - If PSU succeeds, DMM fails: Returns PSU data, DMM=None (partial success)
            - If both fail: Raises RuntimeError (triggers reconnection)
        """
        import logging
        logger = logging.getLogger(__name__)

        result = {}
        any_success = False

        for class_name, poll_method in poll_methods.items():
            try:
                data = poll_method(channel)
                if data:
                    result[class_name] = data
                    any_success = True
                else:
                    # Poll method returned empty dict
                    logger.warning(f"{class_name} poll returned empty data for channel {channel}")
                    result[class_name] = None

            except Exception as e:
                # Poll method raised exception (timeout, serial error, etc.)
                logger.warning(f"Failed to poll {class_name} channel {channel}: {e}")
                result[class_name] = None

        # If all classes failed, raise to trigger reconnection
        if not any_success:
            class_names = list(poll_methods.keys())
            raise RuntimeError(
                f"All classes {class_names} failed to poll channel {channel} - device not responding"
            )

        return result

    # ===== TRANSPORT DELEGATION METHODS =====

    def write(self, data: bytes) -> None:
        """
        Write raw bytes to transport.

        Args:
            data: Raw bytes to write
        """
        self.t.write(data)

    def write_line(self, text: str) -> None:
        """
        Write text line with EOL terminator.

        Args:
            text: Text to write (EOL added automatically)
        """
        self.t.write_line(text)

    def read(self, size: int = 1024) -> bytes:
        """
        Read raw bytes from transport.

        Args:
            size: Maximum number of bytes to read

        Returns:
            Raw bytes read from transport
        """
        return self.t.read(size)

    def read_until_reol(self, max_bytes: int = 1024) -> str:
        """
        Read text until EOL terminator.

        Args:
            max_bytes: Maximum number of bytes to read

        Returns:
            Text string (without EOL terminator)
        """
        return self.t.read_until_reol(max_bytes)

    # ===== HELPER METHODS =====

    def _is_usb_tmc(self) -> bool:
        """
        Check if transport is USB TMC.

        USB TMC devices don't respond to SET commands, so SET operations
        should not attempt to read responses.

        Returns:
            True if transport is USB TMC, False otherwise
        """
        return isinstance(self.t, UsbTmcTransport)

    def _parse_numeric(self, s: Any) -> Optional[float]:
        """
        Extract numeric value from string/bytes response.

        Handles common patterns:
        - Byte/string conversion
        - Scientific notation (1.23E-4, 5.67e+2)
        - Units and whitespace removal (extracts first number)

        Args:
            s: Response from device (str, bytes, or None)

        Returns:
            Numeric value as float, or None if parsing fails

        Examples:
            >>> self._parse_numeric(b"5.0V")
            5.0
            >>> self._parse_numeric("1.23E-4")
            0.000123
            >>> self._parse_numeric("  42  ")
            42.0
            >>> self._parse_numeric(None)
            None
        """
        if s is None:
            return None

        # Convert bytes to string
        if isinstance(s, bytes):
            try:
                s = s.decode('utf-8', 'ignore')
            except Exception:
                return None

        s = str(s).strip()

        # Extract first numeric value (with optional scientific notation)
        m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
        try:
            return float(m.group(0)) if m else None
        except Exception:
            return None

    def _clean_response(self, raw: Any) -> str:
        """
        Normalize device response to clean string.

        Handles common patterns:
        - Bytes to string conversion (UTF-8 with fallback to Latin-1)
        - Whitespace stripping
        - Removing surrounding quotes (single or double)

        Args:
            raw: Raw response from device (bytes, str, or None)

        Returns:
            Cleaned string response (empty string if None)

        Examples:
            >>> self._clean_response(b"  hello  ")
            "hello"
            >>> self._clean_response('"quoted"')
            "quoted"
            >>> self._clean_response(None)
            ""
        """
        if raw is None:
            return ""

        # Convert bytes to string
        if isinstance(raw, (bytes, bytearray)):
            try:
                s = raw.decode('utf-8', errors='ignore')
            except Exception:
                s = raw.decode('latin1', errors='ignore')
        else:
            s = str(raw)

        s = s.strip()

        # Remove surrounding quotes
        if (s.startswith('"') and s.endswith('"')) or \
           (s.startswith("'") and s.endswith("'")):
            s = s[1:-1].strip()

        return s
