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

        Note:
            USB TMC devices don't support select() on Linux. The kernel USBTMC
            driver handles timeouts internally, so we use direct os.read().
        """
        if self._fd is None:
            raise RuntimeError('Transport not open')

        # Direct read - USB TMC driver handles timeouts at kernel level
        try:
            return os.read(self._fd, size)
        except OSError:
            # On timeout or error, return empty bytes
            return b''

    def read_binary(self, max_bytes: int = 4096) -> bytes:
        """
        Read raw binary data without text decoding.

        Use this method for binary data transfers such as:
        - Waveform capture data
        - Screenshot/image data
        - Binary file transfers
        - Raw measurement arrays

        Args:
            max_bytes: Maximum bytes to read

        Returns:
            Raw bytes received (may be less than max_bytes)

        Raises:
            RuntimeError: If transport not open

        Note:
            This is identical to read() but explicitly named for clarity
            when reading binary data. Use read_until_reol() for text commands.
        """
        return self.read(max_bytes)

    def read_until_reol(self, max_bytes: int = 4096) -> str:
        """
        Read until receive EOL terminator.

        Args:
            max_bytes: Maximum bytes to read before giving up

        Returns:
            Response text with EOL terminator stripped

        Raises:
            RuntimeError: If transport not open

        Note:
            USB TMC devices return complete messages in one read operation.
            Reading byte-by-byte causes re-transmission, so we read the full
            response at once and then look for the EOL terminator.
        """
        if self._fd is None:
            raise RuntimeError('Transport not open')

        # USB TMC devices return complete messages - read all at once
        data = self.read(max_bytes)

        if not data:
            return ''

        try:
            text = data.decode('utf-8', errors='ignore')
        except Exception:
            return ''

        # Strip EOL terminators and normalize
        text = text.rstrip('\r\n')

        # Return first line only
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        return lines[0] if lines else ''


def discover_usbtmc_devices():
    """
    Discover available USB TMC devices on the system, including symlinks.

    Returns:
        List of dictionaries with device information:
        [
            {
                "device": "/dev/usbtmc0",
                "name": "usbtmc0",
                "vendor_id": "0x1ab1",  # If available
                "product_id": "0x04ce",  # If available
                "manufacturer": "RIGOL TECHNOLOGIES",  # If available
                "product": "DS1104Z Plus"  # If available
            },
            {
                "device": "/dev/owon-dge-1",  # Symlink
                "name": "owon-dge-1",
                "symlink_target": "/dev/usbtmc0",
                "vendor_id": "0x5345",
                "product_id": "0x1235",
                "manufacturer": "Owon",
                "product": "generator"
            }
        ]
    """
    devices = []
    seen_devices = set()

    def get_device_info(entry, device_path, is_symlink=False, symlink_target=None):
        """Helper to get device info from sysfs."""
        device_info = {
            "device": device_path,
            "name": entry
        }

        if is_symlink and symlink_target:
            device_info["symlink_target"] = symlink_target

        # For symlinks, extract the actual device name from target
        actual_entry = entry
        if is_symlink and symlink_target:
            # Extract usbtmcX from /dev/usbtmcX
            target_name = os.path.basename(symlink_target)
            if target_name.startswith('usbtmc'):
                actual_entry = target_name

        # Try to get USB device info from sysfs
        # /dev/usbtmc0 -> /sys/class/usb/usbtmc0/device
        try:
            sysfs_path = f'/sys/class/usb/{actual_entry}/device'
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

        return device_info

    # Find all /dev/usbtmc* devices
    for entry in os.listdir('/dev'):
        if entry.startswith('usbtmc'):
            device_path = f'/dev/{entry}'
            devices.append(get_device_info(entry, device_path))
            seen_devices.add(device_path)

    # Find all symlinks in /dev that point to USB TMC devices
    for entry in os.listdir('/dev'):
        device_path = f'/dev/{entry}'

        # Skip if already processed
        if device_path in seen_devices:
            continue

        # Check if it's a symlink
        if os.path.islink(device_path):
            try:
                # Resolve the symlink
                target = os.readlink(device_path)

                # Make target absolute if it's relative
                if not os.path.isabs(target):
                    target = os.path.normpath(os.path.join('/dev', target))

                # Check if target is a USB TMC device
                target_name = os.path.basename(target)
                if target_name.startswith('usbtmc'):
                    device_info = get_device_info(
                        entry, device_path,
                        is_symlink=True,
                        symlink_target=target
                    )
                    devices.append(device_info)
                    seen_devices.add(device_path)

            except (OSError, IOError):
                # Broken symlink or permission error
                pass

    return devices
