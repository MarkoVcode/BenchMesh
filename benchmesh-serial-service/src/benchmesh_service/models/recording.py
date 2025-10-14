"""
Database models for data recording.

These models support multi-device recording with pause/resume functionality.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from benchmesh_service.database import Base


class RecordingSeries(Base):
    """
    Recording series metadata.

    Represents a single recording session that can capture data from multiple
    devices and parameters simultaneously.
    """
    __tablename__ = "recording_series"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    interval_seconds = Column(Float, nullable=False)
    channels = Column(Text, nullable=False)  # JSON array of {device_id, parameter, label}
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    paused_at = Column(DateTime)  # NULL if not paused
    pause_duration_seconds = Column(Float, default=0)  # Total time spent paused
    data_points_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to data points
    data_points = relationship(
        "DataPoint",
        back_populates="series",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<RecordingSeries(id={self.id}, name='{self.name}', status={'paused' if self.paused_at else 'recording' if not self.end_time else 'completed'})>"


class DataPoint(Base):
    """
    Individual data point measurement.

    Stores measurements from multiple devices at a single timestamp.
    """
    __tablename__ = "data_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(Integer, ForeignKey("recording_series.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    measurements = Column(Text, nullable=False)  # JSON object with all measurements

    # Relationship to series
    series = relationship("RecordingSeries", back_populates="data_points")

    def __repr__(self):
        return f"<DataPoint(id={self.id}, series_id={self.series_id}, timestamp={self.timestamp})>"
