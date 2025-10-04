import os
import time

import sys
from unittest.mock import patch
import types
import time

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
        self._read_buffer = b""
        self._raise_on_read = False

    def write(self, data: bytes):
        self._written.append(bytes(data))
    def setDTR(self, flag: bool):
        pass
    def setRTS(self, flag: bool):
        pass

    def read(self, size: int = 256) -> bytes:
        if self._raise_on_read:
            raise Exception("read error")
        if self._read_buffer:
            data, self._read_buffer = self._read_buffer[:size], self._read_buffer[size:]
            return data
        return b""

    def close(self):
        self.is_open = False


def make_devices(n=3):
    devs = []
    for i in range(n):
        devs.append({
            'id': f'dev-{i+1}',
            'name': f'Device {i+1}',
            'driver': 'owon_oel',
            'port': f'/dev/ttyFAKE{i+1}',
            'baud': 115200,
            'serial': '8N1',
        })
    return devs


def _get_underlying_serial(m: SerialManager, dev_id: str) -> FakeSerial:
    drv = m.connections[dev_id]
    return getattr(getattr(drv, 't', None), '_ser', None)


def test_establish_connections_opens_all_devices():
    devices = make_devices(4)
    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
    assert set(m.connections.keys()) == {d['id'] for d in devices}
    for dev_id, drv in m.connections.items():
        assert hasattr(drv, 't') and getattr(drv.t, 'is_open', False)
        ser = _get_underlying_serial(m, dev_id)
        assert isinstance(ser, FakeSerial)
        assert ser.is_open is True


def test_establish_connections_tolerates_failures_and_continues():
    devices = make_devices(3)

    def serial_factory(**kw):
        if kw.get('port') == devices[1]['port']:
            raise Exception('open failed')
        return FakeSerial(**kw)

    with patch('benchmesh_service.transport.serial.Serial', side_effect=serial_factory):
        m = SerialManager(devices)
    # two should be connected; the failing one may be absent or present with None
    assert devices[0]['id'] in m.connections
    assert devices[2]['id'] in m.connections
    assert (devices[1]['id'] not in m.connections) or (m.connections[devices[1]['id']] is None)


def test_identify_cadence_uses_manual_clock_and_registry_idn_set():
    # Verify identify attempts follow identify_interval and set IDN upon non-empty response
    devices = make_devices(1)
    from benchmesh_service.clock import ManualClock
    clock = ManualClock(start=0.0)

    class IdentSerial(FakeSerial):
        pass

    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: IdentSerial(**kw)):
        m = SerialManager(devices, clock=clock)
        dev = devices[0]
        dev_id = dev['id']
        # On first call, no IDN yet; FakeSerial read buffer empty -> identify returns '' -> no IDN set
        m._open_or_identify(dev)
        assert 'IDN' not in m.registry[dev_id]
        # Second call without advancing time should NOT attempt identify again
        m._open_or_identify(dev)
        assert 'IDN' not in m.registry[dev_id]
        # Advance by identify interval and preload a response ending with CR
        clock.advance(m.policy.identify_interval)
        # Simulate instrument responding to *IDN?
        ser = getattr(getattr(m.connections[dev_id], 't', None), '_ser', None)
        if ser is not None:
            ser._read_buffer = b"FAKE,IDN\r"
        m._open_or_identify(dev)
        assert m.registry[dev_id].get('IDN') == 'FAKE,IDN'


def test_reconnect_backoff_respected_with_manual_clock():
    devices = make_devices(1)
    from benchmesh_service.clock import ManualClock
    clock = ManualClock(start=0.0)

    opened = {'count': 0}

    class FlakySerial(FakeSerial):
        def __init__(self, **kw):
            opened['count'] += 1
            super().__init__(**kw)

    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FlakySerial(**kw)):
        m = SerialManager(devices, clock=clock)
        dev = devices[0]
        dev_id = dev['id']
        # First open attempt happens on init
        assert m.connections[dev_id] is not None
        # Simulate a drop: clear both public and internal connection state
        m.connections[dev_id] = None
        if dev_id in m.dev_conns:
            m.dev_conns[dev_id].driver = None
        # Immediate call to _open_or_identify should not reopen without advancing time
        m._open_or_identify(dev)
        assert m.connections[dev_id] is None
        # Advance less than reconnect interval
        clock.advance(m.policy.reconnect_interval - 0.1)
        m._open_or_identify(dev)
        assert m.connections[dev_id] is None
        # Advance to satisfy reconnect interval
        clock.advance(0.2)
        m._open_or_identify(dev)
        assert m.connections[dev_id] is not None
        assert opened['count'] >= 2


def test_identify_writes_idn_probe_and_reads_response():
    devices = make_devices(1)
    from benchmesh_service.clock import ManualClock
    clock = ManualClock(start=0.0)

    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices, clock=clock)
        dev = devices[0]
        dev_id = dev['id']
        # First identify attempt will not fire immediately because open just updated last_open_attempt
        m._open_or_identify(dev)
        ser = _get_underlying_serial(m, dev_id)
        assert not any(w for w in ser._written), 'No identify probe should be sent yet'
        # Advance and provide response, then attempt again
        clock.advance(m.policy.identify_interval)
        ser._written.clear()
        ser._read_buffer = b"VENDOR,MODEL,SN\r"
        m._open_or_identify(dev)
        # Should have written the IDN probe and stored the response
        assert any(w for w in ser._written), 'Expected a write during identify probe after interval'
        assert m.registry[dev_id].get('IDN') == 'VENDOR,MODEL,SN'



