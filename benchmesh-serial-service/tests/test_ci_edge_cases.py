import os, sys
from unittest.mock import patch
import pytest

# Ensure package importable
THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from benchmesh_service.serial_manager import SerialManager
from benchmesh_service.poll_worker import DeviceWorker
from benchmesh_service.registry import DeviceRegistry
from benchmesh_service.manifest_resolver import ManifestResolver
from benchmesh_service.metrics import MetricsRecorder

class FakeSerial:
    def __init__(self, port, baudrate=115200, bytesize=None, parity=None, stopbits=None, timeout=1.0, xonxoff=False, rtscts=False, dsrdtr=False):
        self.port = port
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
            out, self._read_buffer = self._read_buffer[:size], self._read_buffer[size:]
            return out
        return b""


def make_devices(n=1, driver='owon_oel'):
    return [{
        'id': f'dev-{i+1}',
        'name': f'Device {i+1}',
        'driver': driver,
        'port': f'/dev/ttyFAKE{i+1}',
        'baud': 115200,
        'serial': '8N1',
    } for i in range(n)]


def test_identify_empty_and_partial_responses_do_not_set_idn(manual_clock):
    devices = make_devices(1)
    with patch('serial.Serial', side_effect=lambda **kw: FakeSerial(**kw)):
        m = SerialManager(devices, clock=manual_clock)
        dev = devices[0]
        dev_id = dev['id']
        # Initial call — not enough time elapsed; no write yet
        m._open_or_identify(dev)
        ser = getattr(getattr(m.connections[dev_id], 't', None), '_ser', None)
        # Recent open may prevent immediate identify write; it is acceptable if no write yet
        if ser is not None:
            assert not ser._written
        # Advance to allow identify and ensure empty identify does not set IDN
        manual_clock.advance(m.policy.identify_interval)
        # Force driver query_identify to return empty string
        drv = m.connections[dev_id]
        setattr(drv, 'query_identify', lambda: '')
        m._open_or_identify(dev)
        assert m.registry[dev_id].get('IDN') is None
        # Now force a proper identify response
        manual_clock.advance(m.policy.identify_interval)
        setattr(drv, 'query_identify', lambda: 'OK,MODEL,SN')
        m._open_or_identify(dev)
        assert m.registry[dev_id].get('IDN') == 'OK,MODEL,SN'


class FakeDrv:
    def __init__(self):
        self.calls = []
    def poll_status(self, ch):
        """Unified multi-class polling - returns data for all classes"""
        self.calls.append(('unified', ch))
        # Return valid PSU data, but malformed DMM data for testing
        return {
            'PSU': {'ok': True, 'ch': ch},
            'DMM': "oops"  # Malformed: non-dict truthy value
        }


def test_poll_worker_handles_malformed_driver_return_and_updates_metrics(manual_clock):
    dev = {
        'id': 'dev-1', 'name': 'SPM', 'driver': 'owon_spm', 'port': '/dev/ttyFAKE1',
        'baud': 115200, 'serial': '8N1', 'model': 'SPM3103',
    }
    registry = DeviceRegistry({'dev-1': {'IDN': 'FAKE'}})
    resolver = ManifestResolver()
    metrics = MetricsRecorder()
    drv = FakeDrv()
    w = DeviceWorker(dev, drv, registry, resolver, metrics=metrics)
    # For unified polling, set 'unified' key instead of per-class
    w.last_probe_class = {'unified': -1e9}

    now = manual_clock.now()
    # Unified polling executes once and returns data for all classes
    # The DMM class data will be malformed but PSU data is valid
    w.run_once(now)

    # Metrics: one unified poll executed
    # With unified polling, we track 'unified' instead of per-class
    assert metrics.polls_total.get(('dev-1','unified')) == 1

    # No failed increments, because the overall result was truthy
    assert metrics.polls_failed.get(('dev-1','unified')) in (None, 0)

    # Registry should have captured PSU status (valid data)
    # DMM may not appear if its data was malformed (non-dict)
    dev_reg = registry.data['dev-1']
    assert 'PSU' in dev_reg and 'status_ch1' in dev_reg['PSU']
