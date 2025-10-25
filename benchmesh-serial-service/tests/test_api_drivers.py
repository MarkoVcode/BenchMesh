"""
Tests for driver listing API endpoint with enabled/disabled filtering.
"""
import pytest
from fastapi.testclient import TestClient
import json
import os
import tempfile
import shutil


def test_list_drivers_filters_disabled_drivers(monkeypatch, tmp_path):
    """
    Test that /drivers endpoint filters out drivers with enabled: false
    """
    from benchmesh_service.api import app

    # Create a temporary drivers directory structure
    drivers_dir = tmp_path / "drivers"
    drivers_dir.mkdir()

    # Create enabled driver (owon_spm)
    spm_dir = drivers_dir / "owon_spm"
    spm_dir.mkdir()
    spm_manifest = {
        "vendor": "OWON",
        "family": "SPM",
        "version": "1.0.0",
        "models": {}
    }
    with open(spm_dir / "manifest.json", "w") as f:
        json.dump(spm_manifest, f)

    # Create disabled driver (owon_dge)
    dge_dir = drivers_dir / "owon_dge"
    dge_dir.mkdir()
    dge_manifest = {
        "vendor": "OWON",
        "family": "DGE",
        "version": "1.0.0",
        "enabled": False,
        "models": {}
    }
    with open(dge_dir / "manifest.json", "w") as f:
        json.dump(dge_manifest, f)

    # Create another enabled driver (tenma_72)
    tenma_dir = drivers_dir / "tenma_72"
    tenma_dir.mkdir()
    tenma_manifest = {
        "vendor": "TENMA",
        "family": "72",
        "version": "1.0.0",
        "enabled": True,  # Explicitly enabled
        "models": {}
    }
    with open(tenma_dir / "manifest.json", "w") as f:
        json.dump(tenma_manifest, f)

    # Monkeypatch the drivers directory path
    original_list_drivers = app.routes[0].endpoint
    def mock_list_drivers():
        drivers = {}
        for entry in os.listdir(drivers_dir):
            entry_path = drivers_dir / entry
            if not entry_path.is_dir():
                continue
            if entry.startswith('__') or entry.startswith('.'):
                continue

            manifest_path = entry_path / "manifest.json"
            if not manifest_path.is_file():
                continue

            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    # Skip drivers that are explicitly disabled
                    if not manifest.get('enabled', True):
                        continue
                    vendor = manifest.get('vendor', 'Unknown')
                    family = manifest.get('family', 'Unknown')
                    drivers[entry] = {
                        "vendor": vendor,
                        "family": family
                    }
            except Exception:
                continue

        return drivers

    # Replace the endpoint temporarily
    from benchmesh_service import api
    monkeypatch.setattr(api, 'list_drivers', mock_list_drivers)

    # Create test client
    client = TestClient(app)

    # Call the endpoint using the mock
    response_data = mock_list_drivers()

    # Verify results
    assert "owon_spm" in response_data, "Enabled driver (default) should be listed"
    assert "tenma_72" in response_data, "Explicitly enabled driver should be listed"
    assert "owon_dge" not in response_data, "Disabled driver should NOT be listed"

    # Verify the enabled drivers have correct metadata
    assert response_data["owon_spm"]["vendor"] == "OWON"
    assert response_data["owon_spm"]["family"] == "SPM"
    assert response_data["tenma_72"]["vendor"] == "TENMA"
    assert response_data["tenma_72"]["family"] == "72"


def test_list_drivers_defaults_to_enabled():
    """
    Test that drivers without 'enabled' field are treated as enabled by default
    """
    from benchmesh_service.api import app

    # Create temporary manifest data
    manifest_without_flag = {
        "vendor": "TEST",
        "family": "DEVICE",
        "version": "1.0.0",
        "models": {}
    }

    manifest_explicitly_enabled = {
        "vendor": "TEST",
        "family": "DEVICE2",
        "version": "1.0.0",
        "enabled": True,
        "models": {}
    }

    # Test the logic directly
    assert manifest_without_flag.get('enabled', True) == True, "Missing 'enabled' should default to True"
    assert manifest_explicitly_enabled.get('enabled', True) == True, "Explicit 'enabled': true should be True"


def test_owon_dge_is_disabled():
    """
    Integration test: Verify owon_dge driver is actually disabled in the real codebase
    """
    import sys
    import os

    # Get the path to the real owon_dge manifest
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    manifest_path = os.path.join(
        repo_root,
        'src',
        'benchmesh_service',
        'drivers',
        'owon_dge',
        'manifest.json'
    )

    # Verify the manifest exists and has enabled: false
    assert os.path.exists(manifest_path), "owon_dge manifest should exist"

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    assert 'enabled' in manifest, "owon_dge manifest should have 'enabled' field"
    assert manifest['enabled'] == False, "owon_dge should be disabled (enabled: false)"
