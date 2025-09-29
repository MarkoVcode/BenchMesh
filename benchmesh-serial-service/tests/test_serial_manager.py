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
    def __init__(self, port, baudrate=115200, bytesize=None, parity=None, stopbits=None, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.is_open = True
        self._written = []
        self._read_buffer = b""
        self._raise_on_read = False

    def write(self, data: bytes):
        self._written.append(bytes(data))

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
            'driver': 'dummy',
            'port': f'/dev/ttyFAKE{i+1}',
            'baud': 115200,
            'serial': '8N1',
            'seol': '\r',
            'reol': '\n',
        })
    return devs


def test_establish_connections_opens_all_devices():
    devices = make_devices(4)
    with patch('benchmesh_service.serial_manager.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
    assert set(m.connections.keys()) == {d['id'] for d in devices}
    for dev_id, ser in m.connections.items():
        assert isinstance(ser, FakeSerial)
        assert ser.is_open is True


def test_establish_connections_tolerates_failures_and_continues():
    devices = make_devices(3)

    def serial_factory(**kw):
        if kw.get('port') == devices[1]['port']:
            raise Exception('open failed')
        return FakeSerial(**kw)

    with patch('benchmesh_service.serial_manager.serial.Serial', side_effect=serial_factory):
        m = SerialManager(devices)
    # two should be connected; the failing one may be absent or present with None
    assert devices[0]['id'] in m.connections
    assert devices[2]['id'] in m.connections
    assert (devices[1]['id'] not in m.connections) or (m.connections[devices[1]['id']] is None)


def test_check_status_probes_and_leaves_connection_on_no_response():
    devices = make_devices(1)
    with patch('benchmesh_service.serial_manager.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
    # No response by default -> connection should remain, just logs
    m.check_status()
    assert m.connections[devices[0]['id']] is not None


def test_check_status_sets_none_on_read_exception():
    devices = make_devices(1)
    with patch('benchmesh_service.serial_manager.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
    ser = m.connections[devices[0]['id']]
    ser._raise_on_read = True
    m.check_status()
    assert m.connections[devices[0]['id']] is None


def test_check_status_writes_probe():
    devices = make_devices(1)
    with patch('benchmesh_service.serial_manager.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
    ser = m.connections[devices[0]['id']]
    m.check_status()
    # Should have attempted to write a probe (*IDN? or EOL)
    assert any(w for w in ser._written), 'Expected at least one write during probe'


def test_reconnect_backoff_and_successful_reopen(monkeypatch):
    devices = make_devices(1)

    opened = {'count': 0}

    class FlakySerial(FakeSerial):
        def __init__(self, **kw):
            opened['count'] += 1
            super().__init__(**kw)

    # First create manager with a working connection
    with patch('benchmesh_service.serial_manager.serial.Serial', side_effect=lambda **kw: FlakySerial(**kw)):
        m = SerialManager(devices)

    # Simulate a read failure to drop the connection to None
    ser = m.connections[devices[0]['id']]
    ser._raise_on_read = True
    m.check_status()
    assert m.connections[devices[0]['id']] is None

    # Before backoff delay, calling check_status should NOT reopen
    t0 = time.time()
    m.last_open_attempt[devices[0]['id']] = t0
    m.check_status()
    assert m.connections[devices[0]['id']] is None

    # After backoff is satisfied, patch Serial again to succeed and ensure reopen happens
    time.sleep(2.05)
    with patch('benchmesh_service.serial_manager.serial.Serial', side_effect=lambda **kw: FlakySerial(**kw)):
        m.check_status()

    assert m.connections[devices[0]['id']] is not None
    assert opened['count'] >= 2  # initial + reopen

