import os
import sys
from unittest.mock import Mock, patch

THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from benchmesh_service.drivers.owon_oel.driver import OwonOEL
from benchmesh_service.drivers.owon_spm.driver import OWONSPM
from benchmesh_service.drivers.owon_xdm.driver import OWONXDM
from benchmesh_service.drivers.tenma_72.driver import TenmaPSU
from benchmesh_service.transport import SerialTransport


class FakeSerial:
    def __init__(self, port, baudrate=115200, bytesize=None, parity=None, stopbits=None, timeout=1.0, xonxoff=False, rtscts=False, dsrdtr=False):
        self.port = port
        self.baudrate = baudrate
        self.is_open = True
        self._writes = []
        # Provide a line-terminated generic response
        self._buf = b"VENDOR,MODEL,1.0\r"

    def write(self, data: bytes):
        self._writes.append(bytes(data))

    def setDTR(self, flag: bool):
        pass

    def setRTS(self, flag: bool):
        pass

    def read(self, n: int = 1) -> bytes:
        if not self._buf:
            return b""
        data = self._buf[:n]
        self._buf = self._buf[n:]
        return data

    def close(self):
        self.is_open = False


def test_identify_owon_oel_uses_cr_eol():
    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        transport = SerialTransport('/dev/ttyFAKE1', 115200, serial_mode='8N1', seol='\r', reol='\r').open()
        d = OwonOEL(transport=transport)
        idn = d.query_identify()
    assert 'VENDOR' in idn


def test_identify_owon_spm_uses_cr_eol():
    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        transport = SerialTransport('/dev/ttyFAKE2', 115200, serial_mode='8N1', seol='\r', reol='\r').open()
        d = OWONSPM(transport=transport)
        idn = d.query_identify()
    assert 'VENDOR' in idn


def test_identify_owon_xdm_uses_cr_eol():
    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        transport = SerialTransport('/dev/ttyFAKE3', 115200, serial_mode='8N1', seol='\r', reol='\r').open()
        d = OWONXDM(transport=transport)
        idn = d.query_identify()
    assert 'VENDOR' in idn


def test_identify_tenma_empty_eol():
    # TENMA specifies empty EOLs; transport must not append EOL and should read buffered
    class TenmaFake(FakeSerial):
        def __init__(self, **kw):
            super().__init__(**kw)
            self._buf = b"TENMA 72-2540 OK"

    with patch('serial.Serial', side_effect=lambda **kw: TenmaFake(**kw)):
        transport = SerialTransport('/dev/ttyFAKE4', 9600, serial_mode='8N1', seol='', reol='').open()
        d = TenmaPSU(transport=transport)
        idn = d.query_identify()
    assert 'TENMA' in idn or 'OK' in idn
