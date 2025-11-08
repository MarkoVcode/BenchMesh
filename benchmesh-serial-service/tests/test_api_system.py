"""
Tests for system API endpoints: /status and /version
"""
import os
import sys
import json
import tempfile
from unittest.mock import patch, Mock

THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import pytest
from fastapi.testclient import TestClient

import benchmesh_service.api as api


class FakeManager:
    """Minimal fake manager for testing system endpoints."""
    def __init__(self, devices=None):
        self.devices = devices or []
        self.connections = {}
        self.dev_locks = {}
        self.dev_conns = {}
        self.unified_polling_enabled = False
    
    def start(self):
        pass
    
    def stop(self):
        pass


@pytest.fixture
def client_with_fake_mgr(monkeypatch):
    """Fixture that provides a test client with fake manager."""
    fake = FakeManager()
    monkeypatch.setattr(api, "_make_manager", lambda: fake)
    with TestClient(api.app) as client:
        yield client, fake


def test_get_status_no_devices(client_with_fake_mgr):
    """Test /status endpoint with no devices."""
    client, _ = client_with_fake_mgr
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["devices_total"] == 0
    assert data["connected"] == 0
    assert data["disconnected"] == 0


def test_get_status_with_devices(monkeypatch):
    """Test /status endpoint with configured devices."""
    fake = FakeManager(devices=[
        {"id": "dev1"},
        {"id": "dev2"},
        {"id": "dev3"}
    ])
    fake.connections = {
        "dev1": Mock(),  # Connected
        "dev2": Mock()   # Connected
        # dev3 not in connections = disconnected
    }
    monkeypatch.setattr(api, "_make_manager", lambda: fake)
    
    with TestClient(api.app) as client:
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["devices_total"] == 3
        assert data["connected"] == 2
        assert data["disconnected"] == 1


def test_get_version_success(client_with_fake_mgr):
    """Test /version endpoint with successful git tag retrieval."""
    client, _ = client_with_fake_mgr
    
    # Create temporary version.json
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "name": "Benchmesh",
            "version": "0.0.51",
            "description": "BenchMesh - Lab Instrument Control System"
        }, f)
        version_file = f.name
    
    try:
        # Mock subprocess to return a fake git tag
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "v0.0.51-87-g6125be0\n"
        
        with patch('subprocess.run', return_value=mock_result):
            # Mock the version.json path
            original_join = os.path.join
            def mock_join(*args):
                if 'version.json' in args:
                    return version_file
                return original_join(*args)
            
            with patch('os.path.join', side_effect=mock_join):
                response = client.get("/version")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check new required fields
        assert data["releaseVersion"] == "v0.0.51-87-g6125be0"
        assert data["applicationName"] == "BenchMesh"
        assert data["displayVersion"] == "BenchMesh v0.0.51-87-g6125be0"
        
        # Check legacy fields for backward compatibility
        assert data["version"] == "0.0.51"
        assert data["name"] == "BenchMesh"
        assert data["description"] == "BenchMesh - Lab Instrument Control System"
        assert data.get("error") is None
    
    finally:
        os.unlink(version_file)


def test_get_version_git_fails(client_with_fake_mgr):
    """Test /version endpoint when git command fails."""
    client, _ = client_with_fake_mgr
    
    # Create temporary version.json
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "name": "Benchmesh",
            "version": "0.0.51",
            "description": "BenchMesh - Lab Instrument Control System"
        }, f)
        version_file = f.name
    
    try:
        # Mock subprocess to simulate git failure
        mock_result = Mock()
        mock_result.returncode = 128  # Git error code
        mock_result.stdout = ""
        
        with patch('subprocess.run', return_value=mock_result):
            # Mock the version.json path
            original_join = os.path.join
            def mock_join(*args):
                if 'version.json' in args:
                    return version_file
                return original_join(*args)
            
            with patch('os.path.join', side_effect=mock_join):
                response = client.get("/version")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return "unknown" when git fails
        assert data["releaseVersion"] == "unknown"
        assert data["applicationName"] == "BenchMesh"
        assert data["displayVersion"] == "BenchMesh unknown"
        
        # Legacy fields should still work
        assert data["version"] == "0.0.51"
    
    finally:
        os.unlink(version_file)


def test_get_version_no_version_json(client_with_fake_mgr):
    """Test /version endpoint when version.json is missing."""
    client, _ = client_with_fake_mgr
    
    # Mock subprocess to return a git tag
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "v1.0.0\n"
    
    with patch('subprocess.run', return_value=mock_result):
        # Point to non-existent version.json
        with patch('os.path.join', return_value='/nonexistent/version.json'):
            response = client.get("/version")
    
    assert response.status_code == 200
    data = response.json()
    
    # Git tag should still work
    assert data["releaseVersion"] == "v1.0.0"
    assert data["applicationName"] == "BenchMesh"
    assert data["displayVersion"] == "BenchMesh v1.0.0"
    
    # Legacy fields should have fallback values
    assert data["version"] == "unknown"
    assert data["name"] == "BenchMesh"
    assert data["description"] == "Lab Instrument Control System"


def test_get_version_subprocess_exception(client_with_fake_mgr):
    """Test /version endpoint when subprocess raises an exception."""
    client, _ = client_with_fake_mgr
    
    # Mock subprocess to raise an exception
    with patch('subprocess.run', side_effect=Exception("Command not found")):
        with patch('os.path.join', return_value='/nonexistent/version.json'):
            response = client.get("/version")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should handle gracefully with "unknown"
    assert data["releaseVersion"] == "unknown"
    assert data["applicationName"] == "BenchMesh"
    assert data["displayVersion"] == "BenchMesh unknown"
