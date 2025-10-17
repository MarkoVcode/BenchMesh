from benchmesh_service.clock import ManualClock
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
            'PSU': {'ok': True, 'psu_ch': ch},
            'DMM': {'ok': True, 'dmm_ch': ch}
        }


def test_manual_clock_controls_per_class_polling_without_sleep():
    dev = {
        'id': 'dev-1',
        'name': 'SPM Combo',
        'driver': 'owon_spm',
        'port': '/dev/ttyFAKE1',
        'baud': 115200,
        'serial': '8N1',
        'model': 'SPM3103',
    }
    # Registry contains IDN so polling is enabled
    registry = DeviceRegistry({'dev-1': {'IDN': 'FAKE'}})
    resolver = ManifestResolver()
    drv = FakeDrv()
    w = DeviceWorker(dev, drv, registry, resolver)

    # Inject manual clock
    clock = ManualClock(start=0.0)

    # For unified polling, set last probe for 'unified' key in the far past
    w.last_probe_class = {'unified': -1e9}

    # At t=0, unified poll is eligible -> polls once and returns data for all classes
    w.run_once(clock.now())
    # Ensure registry updated for available classes, ch1
    reg = registry.data['dev-1']
    # Both PSU and DMM should have data from the unified poll
    assert 'PSU' in reg and 'status_ch1' in reg['PSU']
    assert 'DMM' in reg and 'status_ch1' in reg['DMM']

    # Advance time and verify unified polling continues to work
    # (polling interval from manifest is 2 seconds for SPM3103)
    clock.advance(2.0)
    w.run_once(clock.now())
    # Verify both classes still have status data
    assert 'status_ch1' in registry.data['dev-1']['PSU']
    assert 'status_ch1' in registry.data['dev-1']['DMM']
