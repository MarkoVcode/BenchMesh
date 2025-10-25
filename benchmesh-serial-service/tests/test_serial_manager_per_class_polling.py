import os
import sys
import time
import threading
from unittest.mock import patch

THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from benchmesh_service.serial_manager import SerialManager


class FakeSerial:
    def __init__(self, port, baudrate=115200, bytesize=None, parity=None, stopbits=None, timeout=1.0, xonxoff=False, rtscts=False, dsrdtr=False):
        self.port = port
        self.baudrate = baudrate
        self.is_open = True
        self._written = []
        self._read_buffer = b""
    def write(self, data: bytes):
        self._written.append(bytes(data))
    def setDTR(self, flag: bool):
        pass
    def setRTS(self, flag: bool):
        pass
    def read(self, size: int = 256) -> bytes:
        if self._read_buffer:
            data, self._read_buffer = self._read_buffer[:size], self._read_buffer[size:]
            return data
        return b""
    def close(self):
        self.is_open = False


def test_registry_nested_under_class_and_channels():
    devices = [
        {
            'id': 'dev-1',
            'name': 'SPM Combo',
            'driver': 'owon_spm',
            'port': '/dev/ttyFAKE1',
            'baud': 115200,
            'serial': '8N1',
            'model': 'SPM3103',
        }
    ]
    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
        m.start()
        dev_id = devices[0]['id']
        drv = m.connections[dev_id]

        # Prepare two-class device: PSU and DMM
        # Bypass manifest and force two classes in the manager for this test
        m.dev_class_channels[dev_id] = {'PSU': 1, 'DMM': 1}
        # Ensure per-class intervals are fast for the test
        m.dev_class_poll_interval[dev_id] = {'PSU': 0.1, 'DMM': 0.1}
        m.last_probe_class[dev_id] = {'PSU': 0.0, 'DMM': 0.0}
        # Mark as identified
        m.registry[dev_id]['IDN'] = 'FAKE,IDN'

        def stub_poll(channel=1):
            # Return dict so it is considered a successful poll
            return {'ok': True, 'ch': channel}
        # Provide per-class poll methods as per manifest for SPM (PSU/DMM)
        drv.poll_status_psu = stub_poll  # type: ignore[attr-defined]
        drv.poll_status_dmm = stub_poll  # type: ignore[attr-defined]

        # Allow some time for a few polling cycles
        time.sleep(0.6)

        # Verify registry structure: device -> class -> status_chN
        reg = m.registry.get(dev_id, {})
        assert 'PSU' in reg and isinstance(reg['PSU'], dict)
        assert 'DMM' in reg and isinstance(reg['DMM'], dict)
        # Since SPM manifests 1 channel for PSU and DMM features, expect status_ch1 under each
        assert 'status_ch1' in reg['PSU']
        assert 'status_ch1' in reg['DMM']

        m.stop()
