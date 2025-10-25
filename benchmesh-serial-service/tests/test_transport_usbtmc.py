"""
Tests for USB TMC transport implementation.

Tests cover:
- UsbTmcTransport class functionality
- Device discovery with sysfs metadata
- Error handling and edge cases
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from benchmesh_service.transport.usbtmc import UsbTmcTransport, discover_usbtmc_devices


class TestUsbTmcTransport:
    """Test UsbTmcTransport class functionality."""

    def test_constructor_defaults(self):
        """Test constructor with default parameters."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')

        assert transport.device == '/dev/usbtmc0'
        assert transport.timeout == 1.0
        assert transport.seol == b'\n'
        assert transport.reol == b'\n'
        assert transport._fd is None
        assert not transport.is_open

    def test_constructor_custom_parameters(self):
        """Test constructor with custom parameters."""
        transport = UsbTmcTransport(
            device='/dev/usbtmc1',
            timeout=2.5,
            seol='\r\n',
            reol='\r'
        )

        assert transport.device == '/dev/usbtmc1'
        assert transport.timeout == 2.5
        assert transport.seol == b'\r\n'
        assert transport.reol == b'\r'

    def test_constructor_empty_eol(self):
        """Test constructor with empty EOL strings."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', seol='', reol='')

        assert transport.seol == b''
        assert transport.reol == b''

    @patch('os.path.exists')
    @patch('os.open')
    def test_open_success(self, mock_os_open, mock_exists):
        """Test successful device open."""
        mock_exists.return_value = True
        mock_os_open.return_value = 42  # Mock file descriptor

        transport = UsbTmcTransport(device='/dev/usbtmc0')
        result = transport.open()

        # Should return self for method chaining
        assert result is transport
        assert transport._fd == 42
        assert transport.is_open

        mock_exists.assert_called_once_with('/dev/usbtmc0')
        mock_os_open.assert_called_once_with('/dev/usbtmc0', os.O_RDWR)

    @patch('os.path.exists')
    def test_open_device_not_found(self, mock_exists):
        """Test open when device doesn't exist."""
        mock_exists.return_value = False

        transport = UsbTmcTransport(device='/dev/usbtmc99')

        with pytest.raises(FileNotFoundError, match='USB TMC device not found'):
            transport.open()

        assert transport._fd is None
        assert not transport.is_open

    @patch('os.close')
    def test_close_when_open(self, mock_os_close):
        """Test closing an open transport."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')
        transport._fd = 42

        transport.close()

        mock_os_close.assert_called_once_with(42)
        assert transport._fd is None
        assert not transport.is_open

    def test_close_when_not_open(self):
        """Test closing when transport is not open."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')

        # Should not raise error
        transport.close()

        assert transport._fd is None
        assert not transport.is_open

    @patch('os.close')
    def test_close_cleans_up_on_exception(self, mock_os_close):
        """Test close cleans up _fd even if os.close fails."""
        mock_os_close.side_effect = OSError("Mock error")

        transport = UsbTmcTransport(device='/dev/usbtmc0')
        transport._fd = 42

        # Exception should propagate but cleanup should still happen
        with pytest.raises(OSError, match="Mock error"):
            transport.close()

        # _fd should be None after cleanup (finally block)
        assert transport._fd is None

    @patch('os.write')
    def test_write_success(self, mock_os_write):
        """Test writing raw bytes."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')
        transport._fd = 42

        data = b'*IDN?'
        transport.write(data)

        mock_os_write.assert_called_once_with(42, data)

    def test_write_when_not_open(self):
        """Test write raises error when transport not open."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')

        with pytest.raises(RuntimeError, match='Transport not open'):
            transport.write(b'test')

    @patch('os.write')
    def test_write_line_with_default_eol(self, mock_os_write):
        """Test write_line appends default EOL."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')
        transport._fd = 42

        transport.write_line('*IDN?')

        mock_os_write.assert_called_once_with(42, b'*IDN?\n')

    @patch('os.write')
    def test_write_line_with_custom_eol(self, mock_os_write):
        """Test write_line appends custom EOL."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', seol='\r\n')
        transport._fd = 42

        transport.write_line('*RST')

        mock_os_write.assert_called_once_with(42, b'*RST\r\n')

    @patch('os.write')
    def test_write_line_with_empty_eol(self, mock_os_write):
        """Test write_line with empty EOL."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', seol='')
        transport._fd = 42

        transport.write_line('*RST')

        mock_os_write.assert_called_once_with(42, b'*RST')

    @patch('select.select')
    @patch('os.read')
    def test_read_success(self, mock_os_read, mock_select):
        """Test reading raw bytes with timeout."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')
        transport._fd = 42

        # Simulate data available
        mock_select.return_value = ([42], [], [])
        mock_os_read.return_value = b'OWON,DGE2070'

        result = transport.read(1024)

        assert result == b'OWON,DGE2070'
        mock_select.assert_called_once_with([42], [], [], 1.0)
        mock_os_read.assert_called_once_with(42, 1024)

    @patch('select.select')
    def test_read_timeout(self, mock_select):
        """Test read returns empty bytes on timeout."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', timeout=0.5)
        transport._fd = 42

        # Simulate timeout (no readable data)
        mock_select.return_value = ([], [], [])

        result = transport.read(1024)

        assert result == b''
        mock_select.assert_called_once_with([42], [], [], 0.5)

    def test_read_when_not_open(self):
        """Test read raises error when transport not open."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')

        with pytest.raises(RuntimeError, match='Transport not open'):
            transport.read(1024)

    @patch('select.select')
    @patch('os.read')
    def test_read_until_reol_success(self, mock_os_read, mock_select):
        """Test reading until EOL terminator."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', reol='\n')
        transport._fd = 42

        # Simulate reading byte-by-byte until newline
        mock_select.return_value = ([42], [], [])
        mock_os_read.side_effect = [
            b'O', b'W', b'O', b'N', b',', b'D', b'G', b'E', b'2', b'0', b'7', b'0', b'\n'
        ]

        result = transport.read_until_reol(1024)

        assert result == 'OWON,DGE2070'

    @patch('select.select')
    @patch('os.read')
    def test_read_until_reol_with_crlf(self, mock_os_read, mock_select):
        """Test reading until CRLF terminator."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', reol='\r\n')
        transport._fd = 42

        # Simulate reading until \r\n
        mock_select.return_value = ([42], [], [])
        mock_os_read.side_effect = [
            b'T', b'E', b'S', b'T', b'\r', b'\n'
        ]

        result = transport.read_until_reol(1024)

        assert result == 'TEST'

    @patch('time.time')
    @patch('select.select')
    @patch('os.read')
    def test_read_until_reol_timeout(self, mock_os_read, mock_select, mock_time):
        """Test read_until_reol respects timeout."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', timeout=1.0, reol='\n')
        transport._fd = 42

        # Simulate time progression to trigger timeout
        mock_time.side_effect = [0.0, 0.5, 1.1]  # Start, progress, timeout
        mock_select.return_value = ([42], [], [])
        mock_os_read.return_value = b'X'  # Data without EOL

        result = transport.read_until_reol(1024)

        # Should return partial data before timeout
        assert result == 'X'

    @patch('select.select')
    @patch('os.read')
    def test_read_until_reol_no_eol_configured(self, mock_os_read, mock_select):
        """Test read_until_reol with no EOL configured."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', reol='')
        transport._fd = 42

        # Simulate single read
        mock_select.return_value = ([42], [], [])
        mock_os_read.return_value = b'Line1\nLine2\n'

        result = transport.read_until_reol(1024)

        # Should return first line only
        assert result == 'Line1'

    @patch('select.select')
    @patch('os.read')
    def test_read_until_reol_max_bytes_limit(self, mock_os_read, mock_select):
        """Test read_until_reol respects max_bytes limit."""
        transport = UsbTmcTransport(device='/dev/usbtmc0', reol='\n')
        transport._fd = 42

        # Simulate reading more than max_bytes
        mock_select.return_value = ([42], [], [])
        mock_os_read.side_effect = [b'X'] * 20  # Return 20 bytes

        result = transport.read_until_reol(max_bytes=10)

        # Should stop at max_bytes even without EOL
        assert len(result) == 10

    def test_read_until_reol_when_not_open(self):
        """Test read_until_reol raises error when transport not open."""
        transport = UsbTmcTransport(device='/dev/usbtmc0')

        with pytest.raises(RuntimeError, match='Transport not open'):
            transport.read_until_reol(1024)


class TestDiscoverUsbTmcDevices:
    """Test USB TMC device discovery functionality."""

    @patch('os.listdir')
    @patch('os.path.exists')
    def test_discover_basic(self, mock_exists, mock_listdir):
        """Test basic device discovery without sysfs metadata."""
        mock_listdir.return_value = ['usbtmc0', 'usbtmc1', 'ttyUSB0']  # Mix of devices
        mock_exists.return_value = False  # No sysfs info

        devices = discover_usbtmc_devices()

        assert len(devices) == 2  # Only usbtmc devices
        assert devices[0] == {'device': '/dev/usbtmc0', 'name': 'usbtmc0'}
        assert devices[1] == {'device': '/dev/usbtmc1', 'name': 'usbtmc1'}

    @patch('os.listdir')
    def test_discover_no_devices(self, mock_listdir):
        """Test discovery when no USB TMC devices exist."""
        mock_listdir.return_value = ['ttyUSB0', 'ttyACM0']  # No usbtmc devices

        devices = discover_usbtmc_devices()

        assert devices == []

    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_discover_with_sysfs_metadata(self, mock_file, mock_exists, mock_listdir):
        """Test discovery with full sysfs metadata."""
        mock_listdir.return_value = ['usbtmc0']

        # Mock sysfs paths existence
        def exists_side_effect(path):
            return path in [
                '/sys/class/usb/usbtmc0/device',
                '/sys/class/usb/usbtmc0/device/idVendor',
                '/sys/class/usb/usbtmc0/device/idProduct',
                '/sys/class/usb/usbtmc0/device/manufacturer',
                '/sys/class/usb/usbtmc0/device/product'
            ]
        mock_exists.side_effect = exists_side_effect

        # Mock file reads for USB metadata
        def read_side_effect():
            reads = iter([
                '5345',       # idVendor
                '1234',       # idProduct
                'OWON',       # manufacturer
                'DGE2070'     # product
            ])
            while True:
                try:
                    yield next(reads)
                except StopIteration:
                    yield ''

        mock_file.return_value.read.side_effect = read_side_effect()

        devices = discover_usbtmc_devices()

        assert len(devices) == 1
        device = devices[0]
        assert device['device'] == '/dev/usbtmc0'
        assert device['name'] == 'usbtmc0'
        assert device['vendor_id'] == '0x5345'
        assert device['product_id'] == '0x1234'
        assert device['manufacturer'] == 'OWON'
        assert device['product'] == 'DGE2070'

    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_discover_partial_sysfs_metadata(self, mock_file, mock_exists, mock_listdir):
        """Test discovery with partial sysfs metadata."""
        mock_listdir.return_value = ['usbtmc0']

        # Mock only vendor and product ID available
        def exists_side_effect(path):
            return path in [
                '/sys/class/usb/usbtmc0/device',
                '/sys/class/usb/usbtmc0/device/idVendor',
                '/sys/class/usb/usbtmc0/device/idProduct'
            ]
        mock_exists.side_effect = exists_side_effect

        # Mock file reads
        mock_file.return_value.read.side_effect = ['5345', '1234']

        devices = discover_usbtmc_devices()

        assert len(devices) == 1
        device = devices[0]
        assert device['device'] == '/dev/usbtmc0'
        assert device['name'] == 'usbtmc0'
        assert device['vendor_id'] == '0x5345'
        assert device['product_id'] == '0x1234'
        # manufacturer and product should not be present
        assert 'manufacturer' not in device
        assert 'product' not in device

    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_discover_sysfs_read_error(self, mock_file, mock_exists, mock_listdir):
        """Test discovery handles sysfs read errors gracefully."""
        mock_listdir.return_value = ['usbtmc0']
        mock_exists.return_value = True

        # Simulate file read error
        mock_file.side_effect = IOError("Permission denied")

        devices = discover_usbtmc_devices()

        # Should still return device with basic info
        assert len(devices) == 1
        assert devices[0] == {'device': '/dev/usbtmc0', 'name': 'usbtmc0'}

    @patch('os.listdir')
    def test_discover_multiple_devices(self, mock_listdir):
        """Test discovery finds all USB TMC devices."""
        mock_listdir.return_value = ['usbtmc0', 'usbtmc1', 'ttyUSB0', 'usbtmc2']

        devices = discover_usbtmc_devices()

        # Should find only usbtmc devices (not ttyUSB)
        assert len(devices) == 3
        device_paths = {d['device'] for d in devices}
        assert device_paths == {'/dev/usbtmc0', '/dev/usbtmc1', '/dev/usbtmc2'}

        # Note: discover_usbtmc_devices() does NOT sort
        # Sorting is done in the API layer (api.py line 472)
