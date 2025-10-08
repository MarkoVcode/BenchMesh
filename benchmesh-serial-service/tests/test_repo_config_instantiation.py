import os
import sys
from unittest.mock import patch
import yaml

# Ensure package importable
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
        # Identification reply buffer; sufficient to make identify() happy if used
        self._buf = b"VENDOR,MODEL,1.0\r"

    def write(self, data: bytes):
        self._written.append(bytes(data))

    def read(self, size: int = 256) -> bytes:
        if not self._buf:
            return b""
        data = self._buf[:size]
        self._buf = self._buf[size:]
        return data

    def setDTR(self, flag: bool):
        pass

    def setRTS(self, flag: bool):
        pass

    def close(self):
        self.is_open = False


def test_repo_config_yaml_instantiates_all_devices():
    # Load the config.yaml and verify that SerialManager instantiates a connection
    # for each declared device, without requiring actual serial ports.
    # config.yaml is in benchmesh-serial-service directory
    service_dir = os.path.abspath(os.path.join(THIS_DIR, '..'))
    cfg_path = os.path.join(service_dir, 'config.yaml')
    assert os.path.exists(cfg_path), f"config.yaml not found at {cfg_path}"

    # Also sanity-check the config can be parsed
    with open(cfg_path, 'r') as f:
        cfg = yaml.safe_load(f)
    devices = cfg.get('devices') or []
    expected_ids = {d['id'] for d in devices if 'id' in d}
    assert expected_ids, "Expected at least one device in config.yaml"

    # Patch the serial port class so no real hardware is needed
    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(cfg_path)

    # Ensure the manager has a connection object for each device id and transport is open
    assert set(m.connections.keys()) == expected_ids
    for dev_id in expected_ids:
        drv = m.connections[dev_id]
        assert drv is not None, f"Driver for {dev_id} should not be None"
        t = getattr(drv, 't', None)
        assert t is not None and t.is_open, f"Underlying transport for {dev_id} should be open"
