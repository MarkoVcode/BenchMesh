import threading
import os, sys
THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import types
import pytest
from fastapi.testclient import TestClient

import benchmesh_service.api as api


class FakeDriver:
    def __init__(self):
        self.calls = []
        self.last_arg = None

    def query_identify(self):
        self.calls.append(("query_identify", ()))
        return "FAKE,IDN"

    def set_output(self, ch, v):
        self.calls.append(("set_output", (v,)))
        self.last_arg = v
        return None

    def blow_up(self, *args, **kwargs):
        raise ValueError("boom")


class FakeManager:
    def __init__(self, dev_id: str = "tenmapsu-1"):
        self.devices = [{"id": dev_id}]
        self.connections = {dev_id: FakeDriver()}
        self.dev_locks = {dev_id: threading.RLock()}
        self.unified_polling_enabled = False  # Backward compatibility for tests
    def start(self):
        # No-op for tests
        return None
    def stop(self):
        # No-op for tests
        return None


@pytest.fixture
def client_with_fake_mgr(monkeypatch):
    fake = FakeManager()
    monkeypatch.setattr(api, "_make_manager", lambda: fake)
    # Reinitialize app startup to pick up our fake manager
    with TestClient(api.app) as client:
        yield client, fake


def test_get_instrument_method_success(client_with_fake_mgr):
    client, fake = client_with_fake_mgr
    # Use partial name - API will resolve to query_identify
    path = "/instruments/PSU/tenmapsu-1/1/identify"
    r = client.get(path)
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == path
    assert body["value"] == "FAKE,IDN"
    assert ("query_identify", ()) in fake.connections["tenmapsu-1"].calls


def test_post_instrument_method_success_with_param(client_with_fake_mgr):
    client, fake = client_with_fake_mgr
    # Use partial name - API will resolve to set_output
    r = client.post("/instruments/PSU/tenmapsu-1/1/output/true")
    assert r.status_code == 204
    drv = fake.connections["tenmapsu-1"]
    assert drv.last_arg is True


def test_invalid_class_returns_404(client_with_fake_mgr):
    client, _ = client_with_fake_mgr
    r = client.get("/instruments/XXX/tenmapsu-1/1/identify")
    assert r.status_code == 404


def test_invalid_channel_returns_404(client_with_fake_mgr):
    client, _ = client_with_fake_mgr
    r = client.get("/instruments/PSU/tenmapsu-1/0/identify")
    assert r.status_code == 404
    r = client.get("/instruments/PSU/tenmapsu-1/x/identify")
    assert r.status_code == 404


def test_unknown_method_returns_400(client_with_fake_mgr):
    client, _ = client_with_fake_mgr
    r = client.get("/instruments/PSU/tenmapsu-1/1/no_such_method")
    assert r.status_code == 400


def test_method_exception_returns_400(monkeypatch):
    fake = FakeManager()
    # Replace driver with one that raises
    fake.connections["tenmapsu-1"] = FakeDriver()
    setattr(fake.connections["tenmapsu-1"], "query_identify", fake.connections["tenmapsu-1"].blow_up)
    monkeypatch.setattr(api, "_make_manager", lambda: fake)
    with TestClient(api.app) as client:
        # Use partial name - API will resolve to query_identify
        r = client.get("/instruments/PSU/tenmapsu-1/1/identify")
        assert r.status_code == 400


# ===== Tests for /instruments/{class} filtered endpoint =====

class FakeRegistry:
    """Simple registry mock for instruments list tests"""
    def __init__(self, data=None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)


class ExtendedFakeManager(FakeManager):
    """Extended manager with registry and multiple devices"""
    def __init__(self, devices=None):
        if devices is None:
            devices = [
                {"id": "psu-1", "driver": "owon_spm", "model": "SPM3103"},
                {"id": "dmm-1", "driver": "owon_xdm", "model": "XDM1041"},
                {"id": "tenmapsu-1", "driver": "tenma_72", "model": "72-2540"},
            ]
        super().__init__(dev_id=devices[0]["id"] if devices else "dev-1")
        self.devices = devices
        self.registry = FakeRegistry({
            "psu-1": {"IDN": "OWON,SPM3103,12345,V1.0"},
            "dmm-1": {"IDN": "OWON,XDM1041,67890,V1.0"},
            "tenmapsu-1": {"IDN": "TENMA,72-2540,ABCDE,V1.0"},
        })


def fake_load_manifest_for_tests(driver_key):
    """Mock manifest loader for tests"""
    manifests = {
        "owon_spm": {
            "models": {
                "SPM3103": {
                    "instrument_class": {
                        "PSU": {
                            "features": {"channels": 1},
                            "ui_component": "GenericOWONPSU"
                        },
                        "DMM": {
                            "features": {"channels": 1},
                            "ui_component": "GenericDMM"
                        }
                    }
                }
            }
        },
        "owon_xdm": {
            "models": {
                "XDM1041": {
                    "instrument_class": {
                        "DMM": {
                            "features": {"channels": 1},
                            "ui_component": "GenericDMM"
                        }
                    }
                }
            }
        },
        "tenma_72": {
            "models": {
                "72-2540": {
                    "instrument_class": {
                        "PSU": {
                            "features": {"channels": 1},
                            "ui_component": "GenericPSU"
                        }
                    }
                }
            }
        }
    }
    return manifests.get(driver_key)


@pytest.fixture
def client_with_instruments(monkeypatch):
    """Fixture with multiple instruments for list testing"""
    from benchmesh_service.manifest_resolver import ManifestResolver

    fake = ExtendedFakeManager()
    monkeypatch.setattr(api, "_make_manager", lambda: fake)
    monkeypatch.setattr(api, "_load_manifest", fake_load_manifest_for_tests)

    # Set up manifest resolver
    resolver = ManifestResolver()

    with TestClient(api.app) as client:
        # Manually set the globals after app startup
        api._manager = fake
        api._manifest_resolver = resolver
        yield client, fake


def test_list_instruments_by_class_psu(client_with_instruments):
    """Test filtering instruments by PSU class"""
    client, fake = client_with_instruments
    r = client.get("/instruments/PSU")
    assert r.status_code == 200
    items = r.json()

    # Should return psu-1 (has PSU+DMM) and tenmapsu-1 (has PSU only)
    assert len(items) == 2
    ids = [item["id"] for item in items]
    assert "psu-1" in ids
    assert "tenmapsu-1" in ids
    assert "dmm-1" not in ids  # dmm-1 only has DMM class

    # Each instrument should only have PSU class in classes array
    for item in items:
        assert len(item["classes"]) == 1
        assert item["classes"][0]["class"] == "PSU"
        assert len(item["classes"][0]["channels"]) == 1


def test_list_instruments_by_class_dmm(client_with_instruments):
    """Test filtering instruments by DMM class"""
    client, fake = client_with_instruments
    r = client.get("/instruments/DMM")
    assert r.status_code == 200
    items = r.json()

    # Should return psu-1 (has PSU+DMM) and dmm-1 (has DMM only)
    assert len(items) == 2
    ids = [item["id"] for item in items]
    assert "psu-1" in ids
    assert "dmm-1" in ids
    assert "tenmapsu-1" not in ids  # tenmapsu-1 only has PSU class

    # Each instrument should only have DMM class in classes array
    for item in items:
        assert len(item["classes"]) == 1
        assert item["classes"][0]["class"] == "DMM"


def test_list_instruments_by_class_invalid_class(client_with_instruments):
    """Test that invalid class returns 404"""
    client, fake = client_with_instruments
    r = client.get("/instruments/XXX")
    assert r.status_code == 404
    assert "Invalid instrument class" in r.json()["detail"]


def test_list_instruments_by_class_no_matches(client_with_instruments):
    """Test that valid class with no matching instruments returns 404"""
    client, fake = client_with_instruments
    # ELL is a valid class but no instruments have it
    r = client.get("/instruments/ELL")
    assert r.status_code == 404
    assert "No instruments found" in r.json()["detail"]


def test_list_instruments_by_class_etag_caching(client_with_instruments):
    """Test that ETag caching works for filtered endpoint"""
    client, fake = client_with_instruments

    # First request - get ETag
    r1 = client.get("/instruments/PSU")
    assert r1.status_code == 200
    etag = r1.headers.get("etag")
    assert etag is not None

    # Second request with If-None-Match - should return 304
    r2 = client.get("/instruments/PSU", headers={"if-none-match": etag})
    assert r2.status_code == 304

    # Different class should have different ETag
    r3 = client.get("/instruments/DMM")
    assert r3.status_code == 200
    etag_dmm = r3.headers.get("etag")
    assert etag_dmm != etag


def test_list_instruments_by_class_channels(client_with_instruments):
    """Test that channels are correctly formatted in filtered response"""
    client, fake = client_with_instruments
    r = client.get("/instruments/PSU")
    assert r.status_code == 200
    items = r.json()

    for item in items:
        for cls in item["classes"]:
            assert cls["class"] == "PSU"
            # Check channel format
            for channel in cls["channels"]:
                assert channel.startswith(f"/instruments/PSU/{item['id']}/")
                assert channel.endswith("/1")  # Single channel devices


def test_list_instruments_unfiltered_returns_all(client_with_instruments):
    """Test that /instruments (without filter) still returns all instruments"""
    client, fake = client_with_instruments
    r = client.get("/instruments")
    assert r.status_code == 200
    items = r.json()

    # Should return all 3 devices
    assert len(items) == 3
    ids = [item["id"] for item in items]
    assert "psu-1" in ids
    assert "dmm-1" in ids
    assert "tenmapsu-1" in ids

    # psu-1 should have both PSU and DMM classes
    psu_1 = next(item for item in items if item["id"] == "psu-1")
    assert len(psu_1["classes"]) == 2
    class_names = [cls["class"] for cls in psu_1["classes"]]
    assert "PSU" in class_names
    assert "DMM" in class_names


# ===== Tests for /instruments/{class}/{device_id}/methods endpoint =====

def test_list_methods_basic(client_with_fake_mgr):
    """Test basic method listing endpoint"""
    client, fake = client_with_fake_mgr
    r = client.get("/instruments/PSU/tenmapsu-1/methods")
    assert r.status_code == 200

    data = r.json()
    assert data["device_id"] == "tenmapsu-1"
    assert data["class"] == "PSU"
    assert "methods" in data
    assert isinstance(data["methods"], list)


def test_list_methods_includes_query_methods(client_with_fake_mgr):
    """Test that query methods are included"""
    client, fake = client_with_fake_mgr
    r = client.get("/instruments/PSU/tenmapsu-1/methods")
    assert r.status_code == 200

    methods = r.json()["methods"]
    method_names = [m["name"] for m in methods]

    # Should include query_identify as "identify"
    assert "identify" in method_names

    # Find the identify method
    identify_method = next(m for m in methods if m["name"] == "identify")
    assert identify_method["full_name"] == "query_identify"
    assert identify_method["http_method"] == "GET"
    assert "description" in identify_method
    assert "parameters" in identify_method


def test_list_methods_includes_set_methods(client_with_fake_mgr):
    """Test that set methods are included"""
    client, fake = client_with_fake_mgr
    r = client.get("/instruments/PSU/tenmapsu-1/methods")
    assert r.status_code == 200

    methods = r.json()["methods"]

    # Find a set method
    set_methods = [m for m in methods if m["http_method"] == "POST"]
    assert len(set_methods) > 0

    # Check structure of a set method
    if set_methods:
        set_method = set_methods[0]
        assert "name" in set_method
        assert "full_name" in set_method
        assert set_method["full_name"].startswith("set_")
        assert "description" in set_method
        assert "parameters" in set_method


def test_list_methods_parameter_structure(client_with_fake_mgr):
    """Test that parameter information is correctly structured"""
    client, fake = client_with_fake_mgr
    r = client.get("/instruments/PSU/tenmapsu-1/methods")
    assert r.status_code == 200

    methods = r.json()["methods"]

    # Find a method with parameters
    methods_with_params = [m for m in methods if len(m["parameters"]) > 0]
    assert len(methods_with_params) > 0

    # Check parameter structure
    param = methods_with_params[0]["parameters"][0]
    assert "name" in param
    assert "type" in param
    assert "required" in param
    assert "description" in param


def test_list_methods_includes_examples(client_with_fake_mgr):
    """Test that example URLs are included"""
    client, fake = client_with_fake_mgr
    r = client.get("/instruments/PSU/tenmapsu-1/methods")
    assert r.status_code == 200

    methods = r.json()["methods"]

    # All methods should have examples
    for method in methods:
        assert "example" in method
        assert method["example"].startswith(method["http_method"])
        assert "/instruments/PSU/tenmapsu-1/" in method["example"]


def test_list_methods_invalid_class(client_with_fake_mgr):
    """Test that invalid class returns 404"""
    client, fake = client_with_fake_mgr
    r = client.get("/instruments/XXX/tenmapsu-1/methods")
    assert r.status_code == 404


def test_list_methods_invalid_device(client_with_fake_mgr):
    """Test that invalid device returns error"""
    client, fake = client_with_fake_mgr
    r = client.get("/instruments/PSU/nonexistent/methods")
    assert r.status_code in (400, 404)  # Either is acceptable
