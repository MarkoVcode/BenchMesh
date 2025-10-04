from benchmesh_service.driver_factory import DriverFactory

def test_driver_factory_loads_some_class():
    f = DriverFactory()
    cls = f.load_driver_class('owon_spm')
    assert isinstance(cls, type)
