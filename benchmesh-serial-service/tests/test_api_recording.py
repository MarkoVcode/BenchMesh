"""
Tests for recording API endpoints.

Following TDD principles - these tests are written before API implementation.
"""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from benchmesh_service.database import init_database, Base, get_engine
from benchmesh_service.models.recording import RecordingSeries, DataPoint


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh in-memory database for each test."""
    import os
    os.environ['BENCHMESH_DATA_DIR'] = ':memory:'

    # Force re-initialization
    import benchmesh_service.database as db_module
    db_module._engine = None
    db_module._SessionLocal = None

    init_database()

    yield

    # Clean up
    Base.metadata.drop_all(bind=get_engine())
    db_module._engine = None
    db_module._SessionLocal = None


@pytest.fixture
def mock_serial_manager():
    """Mock serial manager with device driver."""
    mock_driver = Mock()
    mock_driver.query_voltage = Mock(return_value=12.05)
    mock_driver.query_current = Mock(return_value=2.34)

    mock_manager = Mock()
    mock_manager.get_device = Mock(return_value={"status": "connected"})
    mock_manager.get_driver = Mock(return_value=mock_driver)

    return mock_manager


@pytest.fixture
def client(test_db, mock_serial_manager):
    """Create FastAPI test client with mocked dependencies."""
    # Import here to avoid circular dependencies
    from fastapi import FastAPI
    import benchmesh_service.services.recording_service as rs_module
    from benchmesh_service.api_recording import create_recording_router

    # Initialize recording service with mock
    rs_module.recording_service = rs_module.RecordingService(serial_manager=mock_serial_manager)

    # Create test app
    app = FastAPI()
    router = create_recording_router()
    app.include_router(router, prefix="/api/recordings")

    return TestClient(app)


class TestStartRecording:
    """Tests for POST /api/recordings/start endpoint."""

    def test_start_recording_success(self, client):
        """Test successfully starting a recording."""
        response = client.post("/api/recordings/start", json={
            "name": "Test Recording",
            "description": "Test description",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })

        assert response.status_code == 200
        data = response.json()
        assert "series_id" in data
        assert data["name"] == "Test Recording"
        assert data["status"] == "recording"

    def test_start_recording_multi_device(self, client):
        """Test starting a multi-device recording."""
        response = client.post("/api/recordings/start", json={
            "name": "Multi-Device Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                },
                {
                    "device_id": "dmm-1",
                    "class_name": "DMM",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "DMM Voltage"
                }
            ],
            "interval_seconds": 1.0
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recording"

    def test_start_recording_duplicate_name(self, client):
        """Test that duplicate names are rejected."""
        # Start first recording
        response1 = client.post("/api/recordings/start", json={
            "name": "Duplicate Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        assert response1.status_code == 200

        # Try to start second with same name
        response2 = client.post("/api/recordings/start", json={
            "name": "Duplicate Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        assert response2.status_code == 400

    def test_start_recording_missing_fields(self, client):
        """Test that missing required fields return 422."""
        response = client.post("/api/recordings/start", json={
            "name": "Missing Fields"
            # Missing channels and interval_seconds
        })

        assert response.status_code == 422


class TestPauseResumeRecording:
    """Tests for pause/resume endpoints."""

    def test_pause_recording(self, client):
        """Test pausing an active recording."""
        # Start recording
        start_response = client.post("/api/recordings/start", json={
            "name": "Pause Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        series_id = start_response.json()["series_id"]

        # Pause recording
        pause_response = client.post(f"/api/recordings/{series_id}/pause")
        assert pause_response.status_code == 200
        data = pause_response.json()
        assert data["status"] == "paused"
        assert "paused_at" in data

    def test_resume_recording(self, client):
        """Test resuming a paused recording."""
        # Start recording
        start_response = client.post("/api/recordings/start", json={
            "name": "Resume Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        series_id = start_response.json()["series_id"]

        # Pause
        client.post(f"/api/recordings/{series_id}/pause")

        # Resume
        resume_response = client.post(f"/api/recordings/{series_id}/resume")
        assert resume_response.status_code == 200
        data = resume_response.json()
        assert data["status"] == "recording"
        assert data["paused_at"] is None

    def test_pause_nonexistent_recording(self, client):
        """Test pausing a nonexistent recording returns 404."""
        response = client.post("/api/recordings/99999/pause")
        assert response.status_code == 404


class TestStopRecording:
    """Tests for POST /api/recordings/{series_id}/stop endpoint."""

    def test_stop_recording(self, client):
        """Test stopping an active recording."""
        # Start recording
        start_response = client.post("/api/recordings/start", json={
            "name": "Stop Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        series_id = start_response.json()["series_id"]

        # Stop recording
        stop_response = client.post(f"/api/recordings/{series_id}/stop")
        assert stop_response.status_code == 200
        data = stop_response.json()
        assert data["status"] == "stopped"
        assert "data_points_count" in data

    def test_stop_nonexistent_recording(self, client):
        """Test stopping a nonexistent recording returns 404."""
        response = client.post("/api/recordings/99999/stop")
        assert response.status_code == 404


class TestListRecordings:
    """Tests for GET /api/recordings endpoint."""

    def test_list_recordings_empty(self, client):
        """Test listing when no recordings exist."""
        response = client.get("/api/recordings")
        assert response.status_code == 200
        data = response.json()
        assert "recordings" in data
        assert len(data["recordings"]) == 0

    def test_list_recordings_with_data(self, client):
        """Test listing multiple recordings."""
        # Create recordings
        for i in range(3):
            client.post("/api/recordings/start", json={
                "name": f"Recording {i}",
                "channels": [
                    {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
                ],
                "interval_seconds": 1.0
            })

        # List recordings
        response = client.get("/api/recordings")
        assert response.status_code == 200
        data = response.json()
        assert len(data["recordings"]) == 3


class TestGetRecordingDetails:
    """Tests for GET /api/recordings/{series_id} endpoint."""

    def test_get_recording_details(self, client):
        """Test getting details of a specific recording."""
        # Start recording
        start_response = client.post("/api/recordings/start", json={
            "name": "Details Test",
            "description": "Test description",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 2.0
        })
        series_id = start_response.json()["series_id"]

        # Get details
        response = client.get(f"/api/recordings/{series_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["series"]["id"] == series_id
        assert data["series"]["name"] == "Details Test"
        assert data["series"]["description"] == "Test description"
        assert data["series"]["interval_seconds"] == 2.0

    def test_get_nonexistent_recording(self, client):
        """Test getting a nonexistent recording returns 404."""
        response = client.get("/api/recordings/99999")
        assert response.status_code == 404


class TestDeleteRecording:
    """Tests for DELETE /api/recordings/{series_id} endpoint."""

    def test_delete_recording(self, client):
        """Test deleting a recording."""
        # Create recording
        start_response = client.post("/api/recordings/start", json={
            "name": "Delete Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        series_id = start_response.json()["series_id"]

        # Stop it first
        client.post(f"/api/recordings/{series_id}/stop")

        # Delete recording
        delete_response = client.delete(f"/api/recordings/{series_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"

        # Verify it's gone
        get_response = client.get(f"/api/recordings/{series_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_recording(self, client):
        """Test deleting a nonexistent recording returns 404."""
        response = client.delete("/api/recordings/99999")
        assert response.status_code == 404


class TestGetRecordingData:
    """Tests for GET /api/recordings/{series_id}/data endpoint."""

    def test_get_recording_data_empty(self, client):
        """Test getting data from a new recording."""
        # Create recording
        start_response = client.post("/api/recordings/start", json={
            "name": "Data Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        series_id = start_response.json()["series_id"]

        # Get data immediately (may have 0 or a few points)
        response = client.get(f"/api/recordings/{series_id}/data")
        assert response.status_code == 200
        data = response.json()
        assert data["series_id"] == series_id
        assert data["total_points"] >= 0  # May have started collecting
        assert "data_points" in data

    def test_get_recording_data_with_pagination(self, client):
        """Test data pagination."""
        # Create recording
        start_response = client.post("/api/recordings/start", json={
            "name": "Pagination Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        series_id = start_response.json()["series_id"]

        # Get data with pagination
        response = client.get(f"/api/recordings/{series_id}/data?offset=0&limit=100")
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 0
        assert data["limit"] == 100


class TestExportRecording:
    """Tests for GET /api/recordings/{series_id}/export endpoint."""

    def test_export_recording_csv(self, client):
        """Test exporting a recording to CSV."""
        # Create and stop recording
        start_response = client.post("/api/recordings/start", json={
            "name": "Export Test",
            "channels": [
                {
                    "device_id": "psu-1",
                    "class_name": "PSU",
                    "channel": 1,
                    "method_name": "voltage",
                    "label": "PSU Voltage"
                }
            ],
            "interval_seconds": 1.0
        })
        series_id = start_response.json()["series_id"]
        client.post(f"/api/recordings/{series_id}/stop")

        # Export to CSV
        response = client.get(f"/api/recordings/{series_id}/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

    def test_export_nonexistent_recording(self, client):
        """Test exporting a nonexistent recording returns 404."""
        response = client.get("/api/recordings/99999/export")
        assert response.status_code == 404
