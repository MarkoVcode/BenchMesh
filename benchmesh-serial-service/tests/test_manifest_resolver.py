from benchmesh_service.manifest_resolver import ManifestResolver

SAMPLE_DEV = {
    'id': 'dev-1',
    'name': 'SPM Combo',
    'driver': 'owon_spm',
    'port': '/dev/ttyFAKE1',
    'baud': 115200,
    'serial': '8N1',
    'model': 'SPM3103',
}

def test_classes_channels_and_intervals_nested_blocks():
    r = ManifestResolver()
    classes = r.get_classes_and_channels(SAMPLE_DEV)
    assert isinstance(classes, dict) and 'PSU' in classes
    # DMM is nested under PSU in manifest; resolver should detect it
    assert 'DMM' in classes

    intervals = r.get_poll_intervals(SAMPLE_DEV)
    assert 'PSU' in intervals
    assert 'DMM' in intervals

    meth_psu = r.get_poll_method(SAMPLE_DEV, 'PSU')
    meth_dmm = r.get_poll_method(SAMPLE_DEV, 'DMM')
    assert meth_psu is not None
    assert meth_dmm is not None


def test_connection_eol_defaults():
    r = ManifestResolver()
    seol, reol = r.get_connection_eol(SAMPLE_DEV)
    assert isinstance(seol, str) and isinstance(reol, str)
