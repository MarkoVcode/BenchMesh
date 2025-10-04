import os
import sys
import time
import threading
from unittest.mock import patch

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


def make_devices(n=2):
    return [
        {
            'id': f'dev-{i+1}',
            'name': f'Device {i+1}',
            'driver': 'owon_oel',
            'port': f'/dev/ttyFAKE{i+1}',
            'baud': 115200,
            'serial': '8N1',
        }
        for i in range(n)
    ]


def _get_driver(m: SerialManager, dev_id: str):
    return m.connections.get(dev_id)


def test_per_device_threads_poll_independently():
    devices = make_devices(2)
    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
        m.start()

        # Counters and stubs
        calls = {d['id']: 0 for d in devices}
        events = {d['id']: threading.Event() for d in devices}

        # Monkeypatch instance methods to count calls
        for d in devices:
            drv = _get_driver(m, d['id'])
            def _make_stub(dev_id):
                def stub(channel=1):
                    calls[dev_id] += 1
                    events[dev_id].set()
                    return {"ok": True, "dev": dev_id}
                return stub
            drv.poll_status = _make_stub(d['id'])  # type: ignore[attr-defined]
            # Provide IDN to enable polling and force immediate poll on next loop
            m.registry[d['id']]['IDN'] = 'FAKE,IDN'
            m.dev_class_poll_interval[d['id']] = {'ELL': 0.1}
            m.last_probe_class[d['id']] = {'ELL': 0.0}
            m.last_probe[d['id']] = 0.0

        # Wait for first poll to occur for each device
        for d in devices:
            assert events[d['id']].wait(timeout=1.5), f"Device {d['id']} did not poll in time"
            assert calls[d['id']] >= 1

        m.stop()


def test_single_reconnect_attempt_per_window():
    devices = make_devices(1)
    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
        m.start()
        dev_id = devices[0]['id']

        # Force connection to None and allow immediate reconnect
        m.connections[dev_id] = None
        m.last_open_attempt[dev_id] = 0.0

        # Spy reconnect to ensure single invocation
        call_count = {dev_id: 0}
        orig_reconnect = m.reconnect
        def spy_reconnect(device_or_id):
            call_count[dev_id] += 1
            # Provide a minimal stub driver with t.is_open
            class Stub:
                class T:
                    is_open = True
                t = T()
                def poll_status(self, channel=1):
                    return {"ok": True}
                def close(self):
                    pass
            m.connections[dev_id] = Stub()
            return m.connections[dev_id]
        m.reconnect = spy_reconnect  # type: ignore[method-assign]

        # Wait a short time for the worker to attempt reconnect
        time.sleep(0.8)
        assert call_count[dev_id] == 1, f"Expected exactly one reconnect, got {call_count[dev_id]}"

        m.stop()


def test_poll_failure_drops_connection_and_triggers_reconnect():
    devices = make_devices(1)
    with patch('benchmesh_service.transport.serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
        # Ensure immediate poll
        m.last_probe[devices[0]['id']] = 0.0
        m.start()
        dev_id = devices[0]['id']

        # Cause poll_status to fail
        drv = _get_driver(m, dev_id)
        def failing_poll(channel=1):
            raise RuntimeError('boom')
        drv.poll_status = failing_poll  # type: ignore[attr-defined]
        # Ensure the device worker tries immediately but prevent instant reconnect
        # Mark as identified so worker will poll and then drop on failure
        m.registry[dev_id]['IDN'] = 'FAKE,IDN'

        m.last_probe[dev_id] = 0.0
        # speed up poll interval for test determinism (per-class now)
        m.dev_class_poll_interval[dev_id] = {'ELL': 0.1}
        m.last_probe_class[dev_id] = {'ELL': 0.0}

        m.last_open_attempt[dev_id] = time.time()

        # Allow worker loop to run and drop connection
        time.sleep(1.1)
        assert m.connections[dev_id] is None, "Expected connection to be dropped after poll failure"

        # Now install a reconnect spy and allow immediate reconnect
        called = {dev_id: 0}
        def spy_reconnect(device_or_id):
            called[dev_id] += 1
            class Stub:
                class T:
                    is_open = True
                t = T()
                def poll_status(self, channel=1):
                    return {"ok": True}
                def close(self):
                    pass
            m.connections[dev_id] = Stub()
            return m.connections[dev_id]
        m.reconnect = spy_reconnect  # type: ignore[method-assign]
        m.last_open_attempt[dev_id] = 0.0

        time.sleep(0.8)
        assert called[dev_id] >= 1
        assert m.connections[dev_id] is not None

        m.stop()
