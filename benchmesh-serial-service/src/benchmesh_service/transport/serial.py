"""
Serial (RS232/USB-Serial) transport implementation.

This module provides SCPI communication over serial ports (RS232, USB-Serial adapters).
"""

import serial
import time
from typing import Optional
from .base import Transport

BYTESIZE_MAP = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}
PARITY_MAP = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD, 'M': serial.PARITY_MARK, 'S': serial.PARITY_SPACE}
STOPBITS_MAP = {1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2: serial.STOPBITS_TWO}


def parse_serial_mode(mode: str):
    if not mode or len(mode) < 3:
        return (serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE)
    try:
        bits = int(mode[0])
        parity = mode[1].upper()
        stop = float(mode[2:]) if len(mode) > 2 else 1
        return (BYTESIZE_MAP.get(bits, serial.EIGHTBITS), PARITY_MAP.get(parity, serial.PARITY_NONE), STOPBITS_MAP.get(stop, serial.STOPBITS_ONE))
    except Exception:
        return (serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE)


class SerialTransport(Transport):
    """
    RS232/USB-Serial transport implementation.

    Provides SCPI communication over serial ports including:
    - Native RS232 ports
    - USB-to-Serial adapters (FTDI, Prolific, etc.)
    - Virtual COM ports

    Args:
        port: Serial port path (e.g., '/dev/ttyUSB0', 'COM3')
        baudrate: Communication speed (e.g., 9600, 115200)
        serial_mode: Data format as 'XYZ' where X=bits, Y=parity, Z=stop bits
                     (e.g., '8N1' = 8 data bits, no parity, 1 stop bit)
        timeout: Read timeout in seconds
        seol: Send End-of-Line terminator (appended to write_line)
        reol: Receive End-of-Line terminator (stripped from read_until_reol)
    """

    def __init__(self, port: str, baudrate: int, serial_mode: str = '8N1', timeout: float = 1.0, seol: str = '\r', reol: str = '\r'):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.seol = seol.encode() if isinstance(seol, str) else (seol or b'')
        self.reol = reol.encode() if isinstance(reol, str) else (reol or b'')
        self.xonxoff=False
        self.rtscts=False
        self.dsrdtr=False
        self._ser: Optional[serial.Serial] = None
        bytesize, parity, stopbits = parse_serial_mode(serial_mode)
        self._kwargs = dict(port=self.port, baudrate=self.baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits, timeout=self.timeout, xonxoff=self.xonxoff, rtscts=self.rtscts, dsrdtr=self.dsrdtr)

    def open(self) -> 'SerialTransport':
        """
        Open the serial port connection.

        Returns:
            self: Allows method chaining

        Raises:
            serial.SerialException: If port cannot be opened
        """
        self._ser = serial.Serial(**self._kwargs)
        self._ser.setDTR(False)   # Needed for USB-RS232 adapters
        self._ser.setRTS(False)
        time.sleep(0.05)
        return self

    def close(self) -> None:
        """Close the serial port."""
        if self._ser:
            try:
                self._ser.close()
            finally:
                self._ser = None

    @property
    def is_open(self) -> bool:
        """Check if serial port is open and ready."""
        return bool(self._ser and getattr(self._ser, 'is_open', True))

    def write(self, data: bytes) -> None:
        """
        Write raw bytes to serial port.

        Args:
            data: Bytes to write

        Raises:
            RuntimeError: If transport not open
        """
        if not self._ser:
            raise RuntimeError('Transport not open')
        self._ser.write(data)

    def write_line(self, text: str) -> None:
        """
        Write text with send EOL terminator.

        Args:
            text: Text to write (seol automatically appended)

        Raises:
            RuntimeError: If transport not open
        """
        # If seol is empty, just write the text without terminator
        data = text.encode('utf-8') + (self.seol or b'')
        self.write(data)

    def read(self, size: int = 1024) -> bytes:
        """
        Read raw bytes from serial port.

        Args:
            size: Maximum bytes to read

        Returns:
            Bytes received (may be less than size if timeout)

        Raises:
            RuntimeError: If transport not open
        """
        if not self._ser:
            raise RuntimeError('Transport not open')
        return self._ser.read(size)

    def read_until_reol(self, max_bytes: int = 4096) -> str:
        """
        Read until receive EOL terminator.

        Args:
            max_bytes: Maximum bytes to read before giving up

        Returns:
            Response text with EOL terminator stripped

        Raises:
            RuntimeError: If transport not open
        """
        if not self._ser:
            raise RuntimeError('Transport not open')
        if not self.reol:
            data = self._ser.read(max_bytes)
            try:
                text = data.decode('utf-8', errors='ignore')
            except Exception:
                return ''
            # Normalize to a single line without trailing EOLs
            lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            return lines[0] if lines else ''
        # Skip any leading EOL noise, then read until configured EOL
        buf = bytearray()
        skipping = True
        while len(buf) < max_bytes:
            b = self._ser.read(1)
            if not b:
                break
            if skipping and b in (b'\r', b'\n'):
                continue
            skipping = False
            buf += b
            if buf.endswith(self.reol):
                break
        try:
            text = bytes(buf).decode('utf-8', errors='ignore')
        except Exception:
            return ''
        # Strip configured EOL and normalize any CR/LF variations to a single line
        text = text.rstrip('\r\n')
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        return lines[0] if lines else ''
