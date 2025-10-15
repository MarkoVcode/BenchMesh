"""
Tests for database models (RecordingSeries and DataPoint).

Following TDD principles - these tests are written before model implementation.
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError

from benchmesh_service.database import init_database, get_db_context, Base, get_engine
from benchmesh_service.models.recording import RecordingSeries, DataPoint


@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh in-memory database for each test.
    """
    import os
    # Use in-memory database for tests
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


class TestRecordingSeries:
    """Tests for RecordingSeries model."""

    def test_create_series_basic(self, test_db):
        """Test creating a basic recording series."""
        channels = [
            {"device_id": "psu-1", "parameter": "voltage", "label": "PSU Voltage"}
        ]

        with get_db_context() as db:
            series = RecordingSeries(
                name="Test Series 1",
                description="Test description",
                interval_seconds=1.0,
                channels=json.dumps(channels),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series)
            db.commit()
            db.refresh(series)

            assert series.id is not None
            assert series.name == "Test Series 1"
            assert series.description == "Test description"
            assert series.interval_seconds == 1.0
            assert series.channels == json.dumps(channels)
            assert series.start_time is not None
            assert series.end_time is None
            assert series.paused_at is None
            assert series.pause_duration_seconds == 0
            assert series.data_points_count == 0

    def test_create_series_multi_device(self, test_db):
        """Test creating a series with multiple device channels."""
        channels = [
            {"device_id": "psu-1", "parameter": "voltage", "label": "PSU Voltage"},
            {"device_id": "psu-1", "parameter": "current", "label": "PSU Current"},
            {"device_id": "dmm-1", "parameter": "voltage", "label": "DMM Voltage"},
            {"device_id": "ell-1", "parameter": "power", "label": "Load Power"}
        ]

        with get_db_context() as db:
            series = RecordingSeries(
                name="Multi-Device Test",
                interval_seconds=2.0,
                channels=json.dumps(channels),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series)
            db.commit()
            db.refresh(series)

            assert series.id is not None
            parsed_channels = json.loads(series.channels)
            assert len(parsed_channels) == 4
            assert parsed_channels[0]["device_id"] == "psu-1"
            assert parsed_channels[2]["device_id"] == "dmm-1"

    def test_series_name_unique_constraint(self, test_db):
        """Test that series names must be unique."""
        with get_db_context() as db:
            series1 = RecordingSeries(
                name="Unique Name",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "psu-1", "parameter": "voltage"}]),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series1)
            db.commit()

            # Try to create another series with the same name
            series2 = RecordingSeries(
                name="Unique Name",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "dmm-1", "parameter": "voltage"}]),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series2)

            with pytest.raises(IntegrityError):
                db.commit()

    def test_series_pause_resume_tracking(self, test_db):
        """Test pause and resume state tracking."""
        with get_db_context() as db:
            series = RecordingSeries(
                name="Pause Test",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "psu-1", "parameter": "voltage"}]),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series)
            db.commit()
            db.refresh(series)

            # Initially not paused
            assert series.paused_at is None
            assert series.pause_duration_seconds == 0

            # Simulate pause
            pause_time = datetime.now(timezone.utc).replace(tzinfo=None)
            series.paused_at = pause_time
            db.commit()
            db.refresh(series)

            assert series.paused_at == pause_time

            # Simulate resume with duration tracking
            series.paused_at = None
            series.pause_duration_seconds = 120.5  # 2 minutes paused
            db.commit()
            db.refresh(series)

            assert series.paused_at is None
            assert series.pause_duration_seconds == 120.5

    def test_series_completion(self, test_db):
        """Test marking a series as completed."""
        with get_db_context() as db:
            start = datetime.now(timezone.utc).replace(tzinfo=None)
            series = RecordingSeries(
                name="Completion Test",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "psu-1", "parameter": "voltage"}]),
                start_time=start
            )
            db.add(series)
            db.commit()
            db.refresh(series)

            # Complete the series
            end = start + timedelta(hours=1)
            series.end_time = end
            series.data_points_count = 3600
            db.commit()
            db.refresh(series)

            assert series.end_time == end
            assert series.data_points_count == 3600


class TestDataPoint:
    """Tests for DataPoint model."""

    def test_create_data_point(self, test_db):
        """Test creating a data point."""
        with get_db_context() as db:
            # Create series first
            series = RecordingSeries(
                name="Data Point Test",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "psu-1", "parameter": "voltage"}]),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series)
            db.commit()
            db.refresh(series)

            # Create data point
            measurements = {"psu-1.voltage": 12.05}
            point = DataPoint(
                series_id=series.id,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                measurements=json.dumps(measurements)
            )
            db.add(point)
            db.commit()
            db.refresh(point)

            assert point.id is not None
            assert point.series_id == series.id
            assert point.timestamp is not None
            assert point.measurements == json.dumps(measurements)

    def test_data_point_multi_device_measurements(self, test_db):
        """Test storing measurements from multiple devices."""
        with get_db_context() as db:
            # Create series
            channels = [
                {"device_id": "psu-1", "parameter": "voltage"},
                {"device_id": "dmm-1", "parameter": "voltage"},
                {"device_id": "ell-1", "parameter": "power"}
            ]
            series = RecordingSeries(
                name="Multi-Device Measurements",
                interval_seconds=1.0,
                channels=json.dumps(channels),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series)
            db.commit()
            db.refresh(series)

            # Create data point with multi-device measurements
            measurements = {
                "psu-1.voltage": 12.05,
                "dmm-1.voltage": 11.98,
                "ell-1.power": 28.2
            }
            point = DataPoint(
                series_id=series.id,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                measurements=json.dumps(measurements)
            )
            db.add(point)
            db.commit()
            db.refresh(point)

            parsed_measurements = json.loads(point.measurements)
            assert len(parsed_measurements) == 3
            assert parsed_measurements["psu-1.voltage"] == 12.05
            assert parsed_measurements["dmm-1.voltage"] == 11.98
            assert parsed_measurements["ell-1.power"] == 28.2


class TestRelationships:
    """Tests for model relationships."""

    def test_series_data_points_relationship(self, test_db):
        """Test relationship between series and data points."""
        with get_db_context() as db:
            # Create series
            series = RecordingSeries(
                name="Relationship Test",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "psu-1", "parameter": "voltage"}]),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series)
            db.commit()
            db.refresh(series)

            # Add multiple data points
            for i in range(5):
                point = DataPoint(
                    series_id=series.id,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    measurements=json.dumps({"psu-1.voltage": 12.0 + i * 0.1})
                )
                db.add(point)
            db.commit()

            # Refresh and check relationship
            db.refresh(series)
            assert len(series.data_points) == 5

            # Check back-reference
            first_point = series.data_points[0]
            assert first_point.series.id == series.id

    def test_cascade_delete(self, test_db):
        """Test that deleting a series deletes its data points."""
        with get_db_context() as db:
            # Create series with data points
            series = RecordingSeries(
                name="Cascade Test",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "psu-1", "parameter": "voltage"}]),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series)
            db.commit()
            db.refresh(series)

            # Add data points
            for i in range(3):
                point = DataPoint(
                    series_id=series.id,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    measurements=json.dumps({"psu-1.voltage": 12.0 + i})
                )
                db.add(point)
            db.commit()

            series_id = series.id

            # Verify data points exist
            points_before = db.query(DataPoint).filter(DataPoint.series_id == series_id).count()
            assert points_before == 3

            # Delete series
            db.delete(series)
            db.commit()

            # Verify data points were deleted
            points_after = db.query(DataPoint).filter(DataPoint.series_id == series_id).count()
            assert points_after == 0

    def test_query_data_points_by_series(self, test_db):
        """Test querying data points for a specific series."""
        with get_db_context() as db:
            # Create two series
            series1 = RecordingSeries(
                name="Series 1",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "psu-1", "parameter": "voltage"}]),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            series2 = RecordingSeries(
                name="Series 2",
                interval_seconds=1.0,
                channels=json.dumps([{"device_id": "dmm-1", "parameter": "voltage"}]),
                start_time=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(series1)
            db.add(series2)
            db.commit()
            db.refresh(series1)
            db.refresh(series2)

            # Add points to both series
            for i in range(3):
                db.add(DataPoint(
                    series_id=series1.id,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    measurements=json.dumps({"psu-1.voltage": 12.0})
                ))

            for i in range(5):
                db.add(DataPoint(
                    series_id=series2.id,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    measurements=json.dumps({"dmm-1.voltage": 5.0})
                ))
            db.commit()

            # Query points for each series
            series1_points = db.query(DataPoint).filter(DataPoint.series_id == series1.id).all()
            series2_points = db.query(DataPoint).filter(DataPoint.series_id == series2.id).all()

            assert len(series1_points) == 3
            assert len(series2_points) == 5
