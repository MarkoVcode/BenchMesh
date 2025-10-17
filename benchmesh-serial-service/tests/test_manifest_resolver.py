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
    # DMM is also a class for SPM3103
    assert 'DMM' in classes

    # SPM3103 uses unified multi-class polling, so it has device-level polling
    # instead of per-class intervals
    assert r.has_multi_class_polling(SAMPLE_DEV) is True

    # Get the unified poll config
    poll_config = r.get_multi_class_poll_config(SAMPLE_DEV)
    assert poll_config is not None
    assert poll_config['method'] == 'poll_status'
    assert poll_config['interval'] == 2


def test_connection_eol_defaults():
    r = ManifestResolver()
    seol, reol = r.get_connection_eol(SAMPLE_DEV)
    assert isinstance(seol, str) and isinstance(reol, str)
