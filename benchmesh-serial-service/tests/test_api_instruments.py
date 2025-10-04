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

    def identify(self):
        self.calls.append(("identify", ()))
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
    path = "/instruments/PSU/tenmapsu-1/1/identify"
    r = client.get(path)
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == path
    assert body["value"] == "FAKE,IDN"
    assert ("identify", ()) in fake.connections["tenmapsu-1"].calls


def test_post_instrument_method_success_with_param(client_with_fake_mgr):
    client, fake = client_with_fake_mgr
    r = client.post("/instruments/PSU/tenmapsu-1/1/set_output/true")
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
    setattr(fake.connections["tenmapsu-1"], "identify", fake.connections["tenmapsu-1"].blow_up)
    monkeypatch.setattr(api, "_make_manager", lambda: fake)
    with TestClient(api.app) as client:
        r = client.get("/instruments/PSU/tenmapsu-1/1/identify")
        assert r.status_code == 400
