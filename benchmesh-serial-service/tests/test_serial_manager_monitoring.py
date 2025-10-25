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


def make_devices(n=1):
    return [
        {
            'id': f'dev-1',
            'name': f'Device 1',
            'driver': 'owon_oel',
            'port': f'/dev/ttyFAKE1',
            'baud': 115200,
            'serial': '8N1',
        }
    ]


def _get_driver(m: SerialManager, dev_id: str):
    return m.connections.get(dev_id)


def test_poll_empty_clears_idn_and_stops_poll_until_identify():
    devices = make_devices(1)
    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
        m.start()
        dev_id = devices[0]['id']

        # Prepare a poll_status stub: first call returns data, then returns empty
        drv = _get_driver(m, dev_id)
        calls = {'n': 0}
        empty_event = threading.Event()
        def stub_poll(channel=1):
            calls['n'] += 1
            if calls['n'] == 1:
                return {'ok': True}
            else:
                empty_event.set()
                return {}
        drv.poll_status = stub_poll  # type: ignore[attr-defined]

        # Mark as identified so worker will poll
        m.registry[dev_id]['IDN'] = 'FAKE,IDN'
        # Speed up polling (per-class now)
        m.dev_class_poll_interval[dev_id] = {'ELL': 0.1}
        m.last_probe_class[dev_id] = {'ELL': 0.0}
        m.last_probe[dev_id] = 0.0

        # Wait for the empty result to be observed
        assert empty_event.wait(timeout=1.5), 'Timed out waiting for empty poll'

        # Immediately block reconnect attempts for a short window
        m.last_open_attempt[dev_id] = time.time()
        current_calls = calls['n']

        # After empty result, SerialManager should clear IDN, close connection, and stop polling
        time.sleep(0.5)
        assert m.registry.get(dev_id) is not None
        assert 'IDN' not in m.registry[dev_id], 'IDN should be cleared after empty poll'
        # Connection may be re-established by the global monitor, but polling must remain stopped while IDN is empty
        assert calls['n'] == current_calls, 'No further polls should happen until identify succeeds'

        m.stop()


def test_identify_not_called_while_idn_present():
    devices = make_devices(1)


def test_no_polling_when_idn_missing():
    devices = make_devices(1)
    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
        m.start()
        dev_id = devices[0]['id']

        drv = _get_driver(m, dev_id)
        calls = {'n': 0}
        def spy_poll(channel=1):
            calls['n'] += 1
            return {'ok': True}
        drv.poll_status = spy_poll  # type: ignore[attr-defined]

        # Ensure IDN is missing and interval is small (per-class now)
        m.registry[dev_id].pop('IDN', None)
        m.dev_class_poll_interval[dev_id] = {'ELL': 0.1}
        m.last_probe_class[dev_id] = {'ELL': 0.0}
        m.last_probe[dev_id] = 0.0

        # Allow time for potential polling; should not be called without IDN
        time.sleep(0.6)
        assert calls['n'] == 0, 'poll_status must not be called while IDN is missing'

        m.stop()


def test_polling_starts_only_after_idn_set():
    devices = make_devices(1)
    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
        m.start()
        dev_id = devices[0]['id']

        drv = _get_driver(m, dev_id)
        calls = {'n': 0}
        polled = threading.Event()
        def spy_poll(channel=1):
            calls['n'] += 1
            polled.set()
            return {'ok': True}
        drv.poll_status = spy_poll  # type: ignore[attr-defined]

        # Ensure IDN missing and fast interval (per-class now)
        m.registry[dev_id].pop('IDN', None)
        m.dev_class_poll_interval[dev_id] = {'ELL': 0.1}
        m.last_probe_class[dev_id] = {'ELL': 0.0}
        m.last_probe[dev_id] = 0.0

        time.sleep(0.4)
        assert calls['n'] == 0, 'No polling should occur without IDN'

        # Now simulate successful identify by setting IDN
        m.registry[dev_id]['IDN'] = 'FAKE,IDN'

        # Wait for polling to begin
        assert polled.wait(timeout=1.0), 'Polling did not start after IDN was set'
        assert calls['n'] >= 1

        m.stop()

    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices)
        m.start()
        dev_id = devices[0]['id']

        drv = _get_driver(m, dev_id)
        # Wrap identify to count calls AFTER this point
        orig_identify = getattr(drv, 'identify', lambda: None)
        identify_calls = {'n': 0}
        def spy_identify():
            identify_calls['n'] += 1
            return orig_identify()
        setattr(drv, 'identify', spy_identify)

        # Ensure IDN is present and polling is active
        m.registry[dev_id]['IDN'] = 'FAKE,IDN'
        # Provide a stable poll_status stub that always returns a value
        drv.poll_status = lambda channel=1: {'ok': True}  # type: ignore[attr-defined]
        m.dev_class_poll_interval[dev_id] = {'ELL': 0.1}
        m.last_probe_class[dev_id] = {'ELL': 0.0}
        m.last_probe[dev_id] = 0.0

        # Allow some time for polling cycles
        time.sleep(0.5)

        # While IDN present, identify should NOT be called
        assert identify_calls['n'] == 0, 'identify must not be called while IDN present'

        m.stop()
