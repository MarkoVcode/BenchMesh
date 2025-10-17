import time
from unittest.mock import Mock
from benchmesh_service.poll_worker import DeviceWorker
from benchmesh_service.registry import DeviceRegistry
from benchmesh_service.manifest_resolver import ManifestResolver

class FakeDrv:
    def __init__(self):
        self.calls = []
    def poll_status(self, ch):
        """Unified multi-class polling - returns data for all classes"""
        self.calls.append(('unified', ch))
        return {
            'PSU': {'ok': True, 'ch': ch},
            'DMM': {'ok': True, 'ch': ch}
        }

def test_device_worker_run_once_updates_registry(monkeypatch):
    dev = {
        'id': 'dev-1',
        'name': 'SPM Combo',
        'driver': 'owon_spm',
        'port': '/dev/ttyFAKE1',
        'baud': 115200,
        'serial': '8N1',
        'model': 'SPM3103',
    }
    r = DeviceRegistry({'dev-1': {'IDN': 'FAKE'}})
    resolver = ManifestResolver()
    drv = FakeDrv()
    w = DeviceWorker(dev, drv, r, resolver)
    now = time.time()
    w.run_once(now)
    reg = r.data['dev-1']
    assert 'PSU' in reg and 'status_ch1' in reg['PSU']
    assert 'DMM' in reg and 'status_ch1' in reg['DMM']
