"""
Test registry population for all driver types.

This test ensures that IDN and status are properly populated in the registry
for all device classes (PSU, DMM, ELL, SPM) to catch issues like missing
query_identify() calls or poll_status() failures.
"""
import os
import sys
from unittest.mock import patch, Mock

THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from benchmesh_service.serial_manager import SerialManager
from benchmesh_service.clock import ManualClock


class FakeSerial:
    """Fake serial port for testing."""
    def __init__(self, port, baudrate=115200, bytesize=None, parity=None, stopbits=None, timeout=1.0, xonxoff=False, rtscts=False, dsrdtr=False):
        self.port = port
        self.baudrate = baudrate
        self.is_open = True
        self._writes = []
        self._read_buffer = b""
        # Command-response mapping with both \r and no terminator variants
        self._responses = {
            b'*IDN?\r': b'VENDOR,MODEL,1.0\r',
            b'*IDN?': b'TENMA 72-2540 OK',  # TENMA has no EOL
            b'MEAS:ALL:INFO?\r': b'12.0,1.5,18.0,OFF,OFF,OFF\r',  # ELL response
            b'MEAS1?\r': b'+1.23456E+00\r',  # DMM response
            b'FUNCtion?\r': b'"VOLT:DC"\r',  # DMM function
            b'STATUS?': b'\x40\x00\x00\x00\x00\x00\x00\x00',  # PSU binary status (output enabled)
            b'VOUT1?': b'12.00',  # PSU voltage
            b'IOUT1?': b'1.50',  # PSU current
            # SPM/DMM additional responses
            b'MEAS:ALL?\r': b'12.0,1.5,18.0\r',
        }
        # Default response for unmatched commands
        self._default_response = b'OK\r'

    def write(self, data: bytes):
        self._writes.append(bytes(data))
        # Immediately prepare response in read buffer
        if data in self._responses:
            self._read_buffer += self._responses[data]
        else:
            self._read_buffer += self._default_response

    def setDTR(self, flag: bool):
        pass

    def setRTS(self, flag: bool):
        pass

    def read(self, n: int = 1) -> bytes:
        if not self._read_buffer:
            return b""
        # Return up to n bytes from buffer
        data = self._read_buffer[:n]
        self._read_buffer = self._read_buffer[n:]
        return data

    def close(self):
        self.is_open = False


def make_device(dev_id, driver, port):
    """Create a device configuration dictionary."""
    return {
        'id': dev_id,
        'name': f'Test {driver}',
        'driver': driver,
        'port': port,
        'baud': 115200,
        'serial': '8N1'
    }


def test_registry_population_psu():
    """Test that PSU device registry gets populated with IDN."""
    devices = [make_device('psu-1', 'tenma_72', '/dev/ttyFAKE1')]
    clock = ManualClock()

    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices, clock=clock)
        dev = devices[0]

        # Open and identify
        m._open_or_identify(dev)

        # Advance time to allow identify
        clock.advance(m.policy.identify_interval)
        m._open_or_identify(dev)

        # Check IDN is populated - this was the bug with OWON XDM
        assert 'psu-1' in m.registry
        assert m.registry['psu-1'].get('IDN') is not None
        assert 'TENMA' in m.registry['psu-1'].get('IDN', '')


def test_registry_population_dmm():
    """Test that DMM device registry gets populated with IDN.

    This test specifically catches the bug where OWON XDM driver's poll_status()
    was calling self.identify() instead of self.query_identify(), which prevented
    the IDN from being populated correctly.
    """
    devices = [make_device('dmm-1', 'owon_xdm', '/dev/ttyFAKE2')]
    clock = ManualClock()

    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices, clock=clock)
        dev = devices[0]

        # Open and identify
        m._open_or_identify(dev)

        # Advance time to allow identify
        clock.advance(m.policy.identify_interval)
        m._open_or_identify(dev)

        # Check IDN is populated - this was the bug that was reported
        assert 'dmm-1' in m.registry
        assert m.registry['dmm-1'].get('IDN') is not None
        assert 'VENDOR' in m.registry['dmm-1'].get('IDN', '')


def test_registry_population_ell():
    """Test that ELL device registry gets populated with IDN."""
    devices = [make_device('ell-1', 'owon_oel', '/dev/ttyFAKE3')]
    clock = ManualClock()

    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices, clock=clock)
        dev = devices[0]

        # Open and identify
        m._open_or_identify(dev)

        # Advance time to allow identify
        clock.advance(m.policy.identify_interval)
        m._open_or_identify(dev)

        # Check IDN is populated
        assert 'ell-1' in m.registry
        assert m.registry['ell-1'].get('IDN') is not None
        assert 'VENDOR' in m.registry['ell-1'].get('IDN', '')


def test_registry_population_spm():
    """Test that SPM device registry gets populated with IDN."""
    devices = [make_device('spm-1', 'owon_spm', '/dev/ttyFAKE4')]
    clock = ManualClock()

    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices, clock=clock)
        dev = devices[0]

        # Open and identify
        m._open_or_identify(dev)

        # Advance time to allow identify
        clock.advance(m.policy.identify_interval)
        m._open_or_identify(dev)

        # Check IDN is populated
        assert 'spm-1' in m.registry
        assert m.registry['spm-1'].get('IDN') is not None
        assert 'VENDOR' in m.registry['spm-1'].get('IDN', '')


def test_all_drivers_have_query_identify():
    """Test that all drivers implement query_identify() method."""
    from benchmesh_service.drivers.owon_oel.driver import OwonOEL
    from benchmesh_service.drivers.owon_spm.driver import OWONSPM
    from benchmesh_service.drivers.owon_xdm.driver import OWONXDM
    from benchmesh_service.drivers.tenma_72.driver import TenmaPSU

    drivers = {
        'OwonOEL': OwonOEL,
        'OWONSPM': OWONSPM,
        'OWONXDM': OWONXDM,
        'TenmaPSU': TenmaPSU,
    }

    for name, driver_class in drivers.items():
        assert hasattr(driver_class, 'query_identify'), \
            f"{name} driver must have query_identify() method"

        # Check it's a method
        with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
            instance = driver_class('/dev/ttyFAKE', 115200, serial_mode='8N1', seol='\r', reol='\r')
            assert callable(getattr(instance, 'query_identify')), \
                f"{name}.query_identify must be callable"
            instance.close()


def test_poll_status_does_not_call_old_identify():
    """
    Test that poll_status() methods don't call self.identify() (old method).
    They should use self.query_identify() instead.
    """
    # This test checks the source code for the old pattern
    # It's a meta-test to ensure the bug doesn't reappear
    import inspect
    from benchmesh_service.drivers.owon_oel.driver import OwonOEL
    from benchmesh_service.drivers.owon_spm.driver import OWONSPM
    from benchmesh_service.drivers.owon_xdm.driver import OWONXDM
    from benchmesh_service.drivers.tenma_72.driver import TenmaPSU

    drivers = {
        'OwonOEL': OwonOEL,
        'OWONSPM': OWONSPM,
        'OWONXDM': OWONXDM,
        'TenmaPSU': TenmaPSU,
    }

    for name, driver_class in drivers.items():
        if hasattr(driver_class, 'poll_status'):
            source = inspect.getsource(driver_class.poll_status)
            # Check that poll_status doesn't call self.identify()
            assert 'self.identify()' not in source, \
                f"{name}.poll_status() must not call self.identify() - use self.query_identify() instead"
