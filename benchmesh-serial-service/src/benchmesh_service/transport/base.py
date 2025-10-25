"""
Abstract base class for instrument communication transports.

This module defines the common interface that all transport implementations
must follow to support SCPI-compatible message exchange.
"""

from abc import ABC, abstractmethod
from typing import Optional


class Transport(ABC):
    """
    Abstract base class for instrument communication transports.

    All transports must implement SCPI-compatible message exchange patterns:
    - Line-based text communication (write_line, read_until_reol)
    - Binary data support (write, read)
    - Connection lifecycle (open, close, is_open)
    - EOL character handling (seol, reol)

    This abstraction allows the same driver code to work with multiple
    physical transports: Serial (RS232/USB-Serial), USB TMC, TCP/IP, etc.

    Implementations:
    - SerialTransport: RS232/USB-Serial communication
    - UsbTmcTransport: USB Test & Measurement Class (planned)
    - TcpIpTransport: Raw TCP/IP sockets for LXI/SCPI-over-TCP (planned)
    """

    @abstractmethod
    def open(self) -> 'Transport':
        """
        Open the transport connection.

        Returns:
            self: The transport instance (allows chaining: transport.open())

        Raises:
            RuntimeError: If connection fails
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close the transport connection.

        Should be idempotent - safe to call multiple times.
        """
        pass

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """
        Check if transport is connected and ready for communication.

        Returns:
            True if connection is established, False otherwise
        """
        pass

    @abstractmethod
    def write(self, data: bytes) -> None:
        """
        Write raw bytes to the transport.

        Args:
            data: Raw byte data to write

        Raises:
            RuntimeError: If transport is not open
        """
        pass

    @abstractmethod
    def write_line(self, text: str) -> None:
        """
        Write text with EOL terminator appended.

        This is the primary method for sending SCPI commands.

        Args:
            text: Text string to write (EOL automatically appended)

        Raises:
            RuntimeError: If transport is not open
        """
        pass

    @abstractmethod
    def read(self, size: int = 1024) -> bytes:
        """
        Read raw bytes from the transport.

        Args:
            size: Maximum number of bytes to read

        Returns:
            Raw byte data received

        Raises:
            RuntimeError: If transport is not open
        """
        pass

    @abstractmethod
    def read_until_reol(self, max_bytes: int = 4096) -> str:
        """
        Read until receive EOL terminator, return as string.

        This is the primary method for receiving SCPI responses.

        Args:
            max_bytes: Maximum bytes to read before giving up

        Returns:
            Response text with EOL terminator stripped

        Raises:
            RuntimeError: If transport is not open
        """
        pass
