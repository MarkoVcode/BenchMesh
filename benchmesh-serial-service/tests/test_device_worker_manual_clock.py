from benchmesh_service.clock import ManualClock
from benchmesh_service.poll_worker import DeviceWorker
from benchmesh_service.registry import DeviceRegistry
from benchmesh_service.manifest_resolver import ManifestResolver

class FakeDrv:
    def __init__(self):
        self.calls = []
    def poll_status_psu(self, ch):
        self.calls.append(('PSU', ch))
        return {'ok': True, 'psu_ch': ch}
    def poll_status_dmm(self, ch):
        self.calls.append(('DMM', ch))
        return {'ok': True, 'dmm_ch': ch}


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

    # Inject manual intervals and time map
    clock = ManualClock(start=0.0)
    # DeviceWorker expects time via run_once(now)

    # Override per-class interval and last probe map
    w.interval_override = {'PSU': 1.0, 'DMM': 2.0}
    # Set last probes in the far past so both classes are eligible immediately
    w.last_probe_class = {'PSU': -1e9, 'DMM': -1e9}

    # At t=0, both classes eligible -> both should poll once
    w.run_once(clock.now())
    # Ensure registry updated for available classes, ch1
    reg = registry.data['dev-1']
    # PSU should always exist for SPM3103 manifest
    assert 'PSU' in reg and 'status_ch1' in reg['PSU']
    # DMM may be nested depending on manifest; if present, it should have status
    if 'DMM' in reg:
        assert 'status_ch1' in reg['DMM']

    # Advance 1.0s -> PSU eligible again, DMM not yet
    clock.advance(1.0)
    w.run_once(clock.now())
    # Verify PSU status key still present
    assert 'status_ch1' in registry.data['dev-1']['PSU']

    # Advance to 2.0s -> DMM now eligible too (if present)
    clock.advance(1.0)
    w.run_once(clock.now())
    if 'DMM' in registry.data['dev-1']:
        assert 'status_ch1' in registry.data['dev-1']['DMM']
