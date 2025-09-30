import os
import sys
import yaml
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


def test_loads_from_yaml_and_instantiates_all(tmp_path):
    devices = [
        {"id": "d1", "name": "OEL", "driver": "owon_oel", "port": "/dev/ttyX1", "baud": 115200, "serial": "8N1"},
        {"id": "d2", "name": "SPM", "driver": "owon_spm", "port": "/dev/ttyX2", "baud": 115200, "serial": "8N1"},
        {"id": "d3", "name": "XDM", "driver": "owon_xdm", "port": "/dev/ttyX3", "baud": 115200, "serial": "8N1"},
        # Alias case: driver key refers to old name, should resolve to tenma_72 package
        {"id": "d4", "name": "TENMA", "driver": "tenma_psu", "port": "/dev/ttyX4", "baud": 9600, "serial": "8N1"},
    ]
    cfg = {"devices": devices}
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))

    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(str(cfg_path))

    assert set(m.connections.keys()) == {d['id'] for d in devices}
    for dev in devices:
        drv = m.connections[dev['id']]
        assert drv is not None
        t = getattr(drv, 't', None)
        assert t is not None and t.is_open
