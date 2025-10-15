"""
Tests for RecordingService with pause/resume functionality.

Following TDD principles - these tests are written before service implementation.
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from benchmesh_service.database import init_database, get_db_context, Base, get_engine
from benchmesh_service.models.recording import RecordingSeries, DataPoint
from benchmesh_service.services.recording_service import RecordingService


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
    # Use lambdas to accept channel argument and return real values
    mock_driver.query_voltage = lambda ch: 12.05
    mock_driver.query_current = lambda ch: 2.34

    mock_manager = Mock()
    mock_manager.get_device = Mock(return_value={"status": "connected"})
    # Recording service uses connections dict, not get_driver
    mock_manager.connections = {"psu-1": mock_driver}

    return mock_manager


class TestRecordingServiceBasic:
    """Basic recording service tests."""

    @pytest.mark.asyncio
    async def test_start_recording(self, test_db, mock_serial_manager):
        """Test starting a recording."""
        service = RecordingService(serial_manager=mock_serial_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            series = await service.start_recording(
                db=db,
                name="Test Recording",
                channels=channels,
                interval_seconds=1.0,
                description="Test description"
            )

            assert series.id is not None
            assert series.name == "Test Recording"
            assert series.description == "Test description"
            assert series.interval_seconds == 1.0
            assert series.start_time is not None
            assert series.end_time is None
            assert series.paused_at is None

            # Verify background task was created
            assert series.id in service.active_recordings
            assert not service.active_recordings[series.id]["task"].done()

            # Clean up
            await service.stop_recording(db, series.id)

    @pytest.mark.asyncio
    async def test_stop_recording(self, test_db, mock_serial_manager):
        """Test stopping a recording."""
        service = RecordingService(serial_manager=mock_serial_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            series = await service.start_recording(
                db=db,
                name="Stop Test",
                channels=channels,
                interval_seconds=1.0
            )

            series_id = series.id
            assert series_id in service.active_recordings

            # Stop recording
            await service.stop_recording(db, series_id)

            # Verify task was cancelled
            assert series_id not in service.active_recordings

            # Verify series was marked complete
            db.refresh(series)
            assert series.end_time is not None

    @pytest.mark.asyncio
    async def test_multi_device_recording(self, test_db):
        """Test recording from multiple devices."""
        # Mock multiple devices with methods that accept channel argument
        mock_psu = Mock()
        mock_psu.query_voltage = lambda ch: 12.05
        mock_psu.query_current = lambda ch: 2.34

        mock_dmm = Mock()
        mock_dmm.query_voltage = lambda ch: 11.98

        # Mock the connections dict that recording service uses
        mock_connections = {
            "psu-1": mock_psu,
            "dmm-1": mock_dmm
        }

        mock_manager = Mock()
        mock_manager.connections = mock_connections

        service = RecordingService(serial_manager=mock_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"},
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "current", "label": "PSU Current"},
            {"device_id": "dmm-1", "class_name": "DMM", "channel": 1, "method_name": "voltage", "label": "DMM Voltage"}
        ]

        with get_db_context() as db:
            series = await service.start_recording(
                db=db,
                name="Multi-Device Test",
                channels=channels,
                interval_seconds=0.1  # Fast for testing
            )

            # Wait for a few data points
            await asyncio.sleep(0.5)

            # Stop recording
            await service.stop_recording(db, series.id)

            # Verify data points were created
            db.refresh(series)
            assert series.data_points_count > 0

            # Check that measurements include all channels
            point = db.query(DataPoint).filter(
                DataPoint.series_id == series.id
            ).first()

            if point:
                measurements = json.loads(point.measurements)
                # Key format: device_id_class_name_channel_method_name
                assert "psu-1_PSU_1_voltage" in measurements
                assert "psu-1_PSU_1_current" in measurements
                assert "dmm-1_DMM_1_voltage" in measurements


class TestRecordingServicePauseResume:
    """Tests for pause/resume functionality."""

    @pytest.mark.asyncio
    async def test_pause_recording(self, test_db, mock_serial_manager):
        """Test pausing a recording."""
        service = RecordingService(serial_manager=mock_serial_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            series = await service.start_recording(
                db=db,
                name="Pause Test",
                channels=channels,
                interval_seconds=0.1
            )

            # Wait briefly
            await asyncio.sleep(0.2)

            # Pause recording
            await service.pause_recording(db, series.id)

            # Verify state
            db.refresh(series)
            assert series.paused_at is not None
            assert series.id in service.active_recordings
            assert service.active_recordings[series.id]["paused"] is True

            # Get data point count before pause
            points_during_pause = series.data_points_count

            # Wait and verify no new data points
            await asyncio.sleep(0.3)
            db.refresh(series)
            assert series.data_points_count == points_during_pause

            # Clean up
            await service.stop_recording(db, series.id)

    @pytest.mark.asyncio
    async def test_resume_recording(self, test_db, mock_serial_manager):
        """Test resuming a paused recording."""
        service = RecordingService(serial_manager=mock_serial_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            series = await service.start_recording(
                db=db,
                name="Resume Test",
                channels=channels,
                interval_seconds=0.1
            )

            # Pause
            await asyncio.sleep(0.2)
            await service.pause_recording(db, series.id)

            db.refresh(series)
            points_at_pause = series.data_points_count
            pause_time = series.paused_at

            # Wait while paused
            await asyncio.sleep(0.2)

            # Resume
            await service.resume_recording(db, series.id)

            # Verify state
            db.refresh(series)
            assert series.paused_at is None
            assert series.pause_duration_seconds > 0
            assert series.id in service.active_recordings
            assert service.active_recordings[series.id]["paused"] is False

            # Wait and verify new data points are collected
            await asyncio.sleep(0.3)
            db.refresh(series)
            assert series.data_points_count > points_at_pause

            # Clean up
            await service.stop_recording(db, series.id)

    @pytest.mark.asyncio
    async def test_multiple_pause_resume_cycles(self, test_db, mock_serial_manager):
        """Test multiple pause/resume cycles accumulate pause duration."""
        service = RecordingService(serial_manager=mock_serial_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            series = await service.start_recording(
                db=db,
                name="Multiple Pause Test",
                channels=channels,
                interval_seconds=0.1
            )

            # First pause/resume cycle
            await asyncio.sleep(0.1)
            await service.pause_recording(db, series.id)
            await asyncio.sleep(0.2)  # Paused for ~0.2s
            await service.resume_recording(db, series.id)

            db.refresh(series)
            first_pause_duration = series.pause_duration_seconds

            # Second pause/resume cycle
            await asyncio.sleep(0.1)
            await service.pause_recording(db, series.id)
            await asyncio.sleep(0.2)  # Paused for ~0.2s more
            await service.resume_recording(db, series.id)

            db.refresh(series)
            second_pause_duration = series.pause_duration_seconds

            # Verify pause duration accumulated
            assert second_pause_duration > first_pause_duration
            assert second_pause_duration >= 0.4  # At least 0.4s total

            # Clean up
            await service.stop_recording(db, series.id)


class TestRecordingServiceDataCollection:
    """Tests for data collection functionality."""

    @pytest.mark.asyncio
    async def test_data_collection_interval(self, test_db, mock_serial_manager):
        """Test that data is collected at specified intervals."""
        service = RecordingService(serial_manager=mock_serial_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            series = await service.start_recording(
                db=db,
                name="Interval Test",
                channels=channels,
                interval_seconds=0.1  # 100ms interval
            )

            # Wait for multiple intervals
            await asyncio.sleep(0.5)

            await service.stop_recording(db, series.id)

            # Verify data points were collected
            db.refresh(series)
            # Should have ~4-5 points in 0.5 seconds at 0.1s intervals
            assert series.data_points_count >= 3
            assert series.data_points_count <= 7

    @pytest.mark.asyncio
    async def test_error_handling_in_data_collection(self, test_db):
        """Test that errors in data collection don't crash the recording."""
        # Mock driver that throws errors
        mock_driver = Mock()
        mock_driver.query_voltage = Mock(side_effect=Exception("Device error"))

        mock_manager = Mock()
        mock_manager.get_driver = Mock(return_value=mock_driver)

        service = RecordingService(serial_manager=mock_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            series = await service.start_recording(
                db=db,
                name="Error Test",
                channels=channels,
                interval_seconds=0.1
            )

            # Wait briefly
            await asyncio.sleep(0.3)

            # Recording should still be active
            assert series.id in service.active_recordings

            # Clean up
            await service.stop_recording(db, series.id)


class TestRecordingServiceState:
    """Tests for recording service state management."""

    @pytest.mark.asyncio
    async def test_cannot_start_duplicate_name(self, test_db, mock_serial_manager):
        """Test that starting a recording with duplicate name fails."""
        service = RecordingService(serial_manager=mock_serial_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        # Start first recording
        with get_db_context() as db:
            series1 = await service.start_recording(
                db=db,
                name="Duplicate Name Test",
                channels=channels,
                interval_seconds=1.0
            )
            series1_id = series1.id

        # Try to start another with same name (in new session)
        with pytest.raises(Exception):  # Should raise IntegrityError
            with get_db_context() as db:
                await service.start_recording(
                    db=db,
                    name="Duplicate Name Test",
                    channels=channels,
                    interval_seconds=1.0
                )

        # Clean up
        with get_db_context() as db:
            await service.stop_recording(db, series1_id)

    @pytest.mark.asyncio
    async def test_get_active_recordings(self, test_db, mock_serial_manager):
        """Test getting list of active recordings."""
        service = RecordingService(serial_manager=mock_serial_manager)

        channels = [
            {"device_id": "psu-1", "class_name": "PSU", "channel": 1, "method_name": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            # Start multiple recordings
            series1 = await service.start_recording(
                db=db,
                name="Active Test 1",
                channels=channels,
                interval_seconds=1.0
            )

            series2 = await service.start_recording(
                db=db,
                name="Active Test 2",
                channels=channels,
                interval_seconds=1.0
            )

            # Check active recordings
            active = service.get_active_recording_ids()
            assert series1.id in active
            assert series2.id in active

            # Stop one
            await service.stop_recording(db, series1.id)

            # Check again
            active = service.get_active_recording_ids()
            assert series1.id not in active
            assert series2.id in active

            # Clean up
            await service.stop_recording(db, series2.id)
