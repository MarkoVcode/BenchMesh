"""
USB TMC (Test & Measurement Class) transport implementation.

This module provides SCPI communication over USB TMC protocol (IEEE 488.2 over USB).
USB TMC devices appear as /dev/usbtmc* on Linux and support direct read/write operations.
"""

import os
import time
from typing import Optional
from .base import Transport


class UsbTmcTransport(Transport):
    """
    USB TMC transport implementation.

    Provides SCPI communication over USB Test & Measurement Class (IEEE 488.2):
    - Direct USB connection to modern instruments
    - No baud rate or serial parameters needed
    - Standard TMC protocol handling

    Args:
        device: USB TMC device path (e.g., '/dev/usbtmc0', '/dev/usbtmc1')
        timeout: Read timeout in seconds
        seol: Send End-of-Line terminator (appended to write_line)
        reol: Receive End-of-Line terminator (stripped from read_until_reol)
    """

    def __init__(self, device: str, timeout: float = 1.0, seol: str = '\n', reol: str = '\n'):
        self.device = device
        self.timeout = timeout
        self.seol = seol.encode() if isinstance(seol, str) else (seol or b'')
        self.reol = reol.encode() if isinstance(reol, str) else (reol or b'')
        self._fd: Optional[int] = None

    def open(self) -> 'UsbTmcTransport':
        """
        Open the USB TMC device.

        Returns:
            self: Allows method chaining

        Raises:
            FileNotFoundError: If device path doesn't exist
            PermissionError: If insufficient permissions (need read/write access)
            OSError: If device cannot be opened
        """
        if not os.path.exists(self.device):
            raise FileNotFoundError(f"USB TMC device not found: {self.device}")

        # Open device file descriptor with read/write access
        self._fd = os.open(self.device, os.O_RDWR)
        return self

    def close(self) -> None:
        """Close the USB TMC device."""
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None

    @property
    def is_open(self) -> bool:
        """Check if USB TMC device is open and ready."""
        return self._fd is not None

    def write(self, data: bytes) -> None:
        """
        Write raw bytes to USB TMC device.

        Args:
            data: Bytes to write

        Raises:
            RuntimeError: If transport not open
            OSError: If write fails
        """
        if self._fd is None:
            raise RuntimeError('Transport not open')
        os.write(self._fd, data)

    def write_line(self, text: str) -> None:
        """
        Write text with send EOL terminator.

        Args:
            text: Text to write (seol automatically appended)

        Raises:
            RuntimeError: If transport not open
        """
        data = text.encode('utf-8') + (self.seol or b'')
        self.write(data)

    def read(self, size: int = 1024) -> bytes:
        """
        Read raw bytes from USB TMC device.

        Args:
            size: Maximum bytes to read

        Returns:
            Bytes received (may be less than size)

        Raises:
            RuntimeError: If transport not open
            OSError: If read fails
        """
        if self._fd is None:
            raise RuntimeError('Transport not open')

        # USB TMC read with timeout handling
        # Use select for timeout support
        import select
        readable, _, _ = select.select([self._fd], [], [], self.timeout)

        if not readable:
            return b''  # Timeout

        return os.read(self._fd, size)

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
        if self._fd is None:
            raise RuntimeError('Transport not open')

        if not self.reol:
            # No EOL configured - read once and return first line
            data = self.read(max_bytes)
            try:
                text = data.decode('utf-8', errors='ignore')
            except Exception:
                return ''
            # Normalize to single line
            lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            return lines[0] if lines else ''

        # Read until configured EOL terminator
        buf = bytearray()
        start_time = time.time()

        while len(buf) < max_bytes:
            # Check timeout
            if time.time() - start_time > self.timeout:
                break

            chunk = self.read(1)  # Read one byte at a time
            if not chunk:
                break

            buf += chunk

            if buf.endswith(self.reol):
                break

        try:
            text = bytes(buf).decode('utf-8', errors='ignore')
        except Exception:
            return ''

        # Strip configured EOL and normalize
        text = text.rstrip('\r\n')
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        return lines[0] if lines else ''


def discover_usbtmc_devices():
    """
    Discover available USB TMC devices on the system.

    Returns:
        List of dictionaries with device information:
        [
            {
                "device": "/dev/usbtmc0",
                "vendor_id": "0x1ab1",  # If available
                "product_id": "0x04ce",  # If available
                "manufacturer": "RIGOL TECHNOLOGIES",  # If available
                "product": "DS1104Z Plus"  # If available
            }
        ]
    """
    devices = []

    # Find all /dev/usbtmc* devices
    for entry in os.listdir('/dev'):
        if entry.startswith('usbtmc'):
            device_path = f'/dev/{entry}'

            device_info = {
                "device": device_path,
                "name": entry
            }

            # Try to get USB device info from sysfs
            # /dev/usbtmc0 -> /sys/class/usb/usbtmc0/device
            try:
                sysfs_path = f'/sys/class/usb/{entry}/device'
                if os.path.exists(sysfs_path):
                    # Read vendor ID
                    vendor_path = os.path.join(sysfs_path, 'idVendor')
                    if os.path.exists(vendor_path):
                        with open(vendor_path, 'r') as f:
                            device_info['vendor_id'] = f'0x{f.read().strip()}'

                    # Read product ID
                    product_path = os.path.join(sysfs_path, 'idProduct')
                    if os.path.exists(product_path):
                        with open(product_path, 'r') as f:
                            device_info['product_id'] = f'0x{f.read().strip()}'

                    # Read manufacturer
                    mfr_path = os.path.join(sysfs_path, 'manufacturer')
                    if os.path.exists(mfr_path):
                        with open(mfr_path, 'r') as f:
                            device_info['manufacturer'] = f.read().strip()

                    # Read product name
                    prod_path = os.path.join(sysfs_path, 'product')
                    if os.path.exists(prod_path):
                        with open(prod_path, 'r') as f:
                            device_info['product'] = f.read().strip()
            except Exception:
                # Sysfs read failed - device info will be incomplete
                pass

            devices.append(device_info)

    return devices
