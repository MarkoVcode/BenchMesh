# Data Recording Feature - Implementation Plan

## Overview

Add instrument data recording capability to BenchMesh with SQLite backend storage, supporting both web and Electron deployments with a unified architecture.

## Requirements Summary

1. **Record selected readings** from instruments (configurable)
2. **Multi-device recording** - record parameters from DIFFERENT devices in ONE series
3. **Works in both** web app (browser) and Electron app
4. **SQLite database** for persistent storage
5. **High-performance** - doesn't impact application performance
6. **Multiple recording series** with custom names
7. **Real-time charts** with stunning visuals (live updates while recording)
8. **Pause and Resume** support (not just stop)
9. **DB management UI**:
   - View all recording series
   - Delete selected series (manual only, no auto-cleanup)
   - Export individual series to CSV
   - Separate window/page with real-time charts

## Architecture Decision

### Database: SQLite on Backend

**Why Backend SQLite?**
- ✅ Works identically for web and Electron (no frontend differences)
- ✅ Python has excellent SQLite support (sqlite3, SQLAlchemy)
- ✅ Single file database, easy backup/export
- ✅ No separate database server needed
- ✅ High performance for time-series data
- ✅ Configurable storage location

**Storage Location:**
- Web deployment: `/opt/benchmesh/data/recordings.db`
- Electron: User data directory (e.g., `~/.benchmesh/recordings.db`)
- Configurable via `BENCHMESH_DATA_DIR` environment variable

### Data Flow

```
┌─────────────────┐
│  Frontend UI    │
│  (React)        │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI        │
│  Backend        │
└────────┬────────┘
         │ SQLAlchemy
         ▼
┌─────────────────┐
│  SQLite DB      │
│  recordings.db  │
└─────────────────┘
         ▲
         │ Background
         │ Recording Task
┌────────┴────────┐
│ Recording       │
│ Service         │
│ (Async polling) │
└─────────────────┘
```

## Database Schema

### Table: `recording_series`

Stores metadata about each recording session. Supports multi-device recording.

```sql
CREATE TABLE recording_series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    interval_seconds REAL NOT NULL,  -- Recording interval (e.g., 1.0 = 1 second)
    channels TEXT NOT NULL,          -- JSON array of channels (device + parameter pairs)
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,              -- NULL if still recording
    paused_at TIMESTAMP,             -- NULL if not paused, timestamp if paused
    pause_duration_seconds REAL DEFAULT 0,  -- Total time spent paused
    data_points_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example channels JSON:
-- [
--   {"device_id": "psu-1", "parameter": "voltage", "label": "PSU Voltage"},
--   {"device_id": "psu-1", "parameter": "current", "label": "PSU Current"},
--   {"device_id": "dmm-1", "parameter": "voltage", "label": "Load Voltage"},
--   {"device_id": "ell-1", "parameter": "power", "label": "Load Power"}
-- ]
```

### Table: `data_points`

Stores individual measurement points with multi-device support.

```sql
CREATE TABLE data_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    measurements TEXT NOT NULL,      -- JSON object with all channel measurements
    FOREIGN KEY (series_id) REFERENCES recording_series(id) ON DELETE CASCADE
);

CREATE INDEX idx_data_points_series_id ON data_points(series_id);
CREATE INDEX idx_data_points_timestamp ON data_points(timestamp);
CREATE INDEX idx_data_points_series_timestamp ON data_points(series_id, timestamp);

-- Example measurements JSON (multi-device):
-- {
--   "psu-1.voltage": 12.05,
--   "psu-1.current": 2.34,
--   "dmm-1.voltage": 11.98,
--   "ell-1.power": 28.2
-- }
```

### Estimated Storage

- Recording series metadata: ~500 bytes per series
- Data point: ~150 bytes per point (timestamp + 3-5 measurements)
- 1 hour at 1Hz = 3,600 points = ~540 KB
- 24 hours at 1Hz = 86,400 points = ~13 MB
- 1 week at 1Hz = ~90 MB

## Real-Time Charting System

### Charting Library: Apache ECharts

**Why ECharts?**
- ✅ **Stunning visuals** - Professional, publication-quality charts
- ✅ **High performance** - WebGL rendering for 100k+ data points
- ✅ **Real-time updates** - Smooth animations and live data streaming
- ✅ **Interactive** - Zoom, pan, data zoom, hover tooltips
- ✅ **Multi-axis support** - Different Y-axes for different units
- ✅ **Themes** - Dark mode support, customizable
- ✅ **Export** - Built-in PNG/SVG export
- ✅ **React integration** - echarts-for-react library

**Alternative**: Plotly.js (also excellent, more scientific-focused)

### Live Data Streaming

**Architecture**:
```
Backend Recording Loop
  ↓ (every data point)
WebSocket Broadcast
  ↓
Frontend Chart
  ↓ (append to series)
ECharts Update (smooth animation)
```

**WebSocket Endpoint**: `ws://localhost:57666/ws/recordings/{series_id}`

**Message Format**:
```json
{
  "type": "data_point",
  "series_id": 1,
  "timestamp": "2025-10-14T10:00:05Z",
  "measurements": {
    "psu-1.voltage": 12.05,
    "psu-1.current": 2.34,
    "dmm-1.voltage": 11.98,
    "ell-1.power": 28.2
  }
}
```

### Chart Configuration

**Multiple Y-Axes Example**:
- Left Y-axis: Voltage (V)
- Right Y-axis 1: Current (A)
- Right Y-axis 2: Power (W)

**Chart Features**:
- Real-time line charts with smooth transitions
- Data zoom (drag to zoom into time range)
- Legend (show/hide series)
- Hover tooltips with all values at timestamp
- Auto-scaling Y-axes
- Time-based X-axis
- Grid lines and axis labels
- Dark/light theme support

## API Endpoints

### Recording Management

```python
# Start a new recording (multi-device)
POST /api/recordings/start
Body: {
    "name": "Battery Discharge Test 1",
    "description": "Testing 18650 cell discharge at 1A",
    "interval_seconds": 1.0,
    "channels": [
        {"device_id": "psu-1", "parameter": "voltage", "label": "PSU Voltage"},
        {"device_id": "psu-1", "parameter": "current", "label": "PSU Current"},
        {"device_id": "dmm-1", "parameter": "voltage", "label": "Load Voltage"},
        {"device_id": "ell-1", "parameter": "power", "label": "Load Power"}
    ]
}
Response: {
    "series_id": 1,
    "name": "Battery Discharge Test 1",
    "status": "recording"
}

# Pause a recording
POST /api/recordings/{series_id}/pause
Response: {
    "series_id": 1,
    "status": "paused",
    "paused_at": "2025-10-14T10:30:00Z"
}

# Resume a paused recording
POST /api/recordings/{series_id}/resume
Response: {
    "series_id": 1,
    "status": "recording",
    "resumed_at": "2025-10-14T10:32:00Z"
}

# Stop a recording (final)
POST /api/recordings/{series_id}/stop
Response: {
    "series_id": 1,
    "status": "stopped",
    "data_points_count": 3600,
    "duration_seconds": 3480,  // Excluding pause time
    "pause_duration_seconds": 120
}

# List all recording series
GET /api/recordings
Response: {
    "series": [
        {
            "id": 1,
            "name": "Battery Discharge Test 1",
            "device_id": "psu-1",
            "device_name": "TENMA PSU",
            "start_time": "2025-10-14T10:00:00Z",
            "end_time": "2025-10-14T11:00:00Z",
            "data_points_count": 3600,
            "status": "completed"
        }
    ]
}

# Get recording details
GET /api/recordings/{series_id}
Response: {
    "id": 1,
    "name": "Battery Discharge Test 1",
    "description": "Testing 18650 cell discharge at 1A",
    "device_id": "psu-1",
    "interval_seconds": 1.0,
    "parameters": ["voltage", "current", "power"],
    "start_time": "2025-10-14T10:00:00Z",
    "end_time": "2025-10-14T11:00:00Z",
    "data_points_count": 3600
}

# Delete a recording series
DELETE /api/recordings/{series_id}
Response: {
    "status": "deleted",
    "series_id": 1
}
```

### Data Query

```python
# Get data points for a series
GET /api/recordings/{series_id}/data?offset=0&limit=1000
Response: {
    "series_id": 1,
    "total_points": 3600,
    "offset": 0,
    "limit": 1000,
    "data": [
        {
            "timestamp": "2025-10-14T10:00:00Z",
            "voltage": 12.05,
            "current": 2.34,
            "power": 28.2
        },
        // ... more points
    ]
}

# Export to CSV
GET /api/recordings/{series_id}/export/csv
Response: CSV file download
Headers: Content-Disposition: attachment; filename="battery-test-1.csv"
```

### Active Recordings

```python
# Get currently active recordings
GET /api/recordings/active
Response: {
    "active": [
        {
            "series_id": 1,
            "name": "Battery Discharge Test 1",
            "device_id": "psu-1",
            "started_at": "2025-10-14T10:00:00Z",
            "duration_seconds": 3600,
            "data_points_count": 3600
        }
    ]
}
```

## Backend Implementation

### 1. Database Models (SQLAlchemy)

```python
# benchmesh-serial-service/src/benchmesh_service/models/recording.py

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from benchmesh_service.database import Base

class RecordingSeries(Base):
    __tablename__ = "recording_series"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    device_id = Column(String, nullable=False)
    device_name = Column(String)
    interval_seconds = Column(Float, nullable=False)
    parameters = Column(Text, nullable=False)  # JSON array
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime)
    data_points_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    data_points = relationship("DataPoint", back_populates="series", cascade="all, delete-orphan")

class DataPoint(Base):
    __tablename__ = "data_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(Integer, ForeignKey("recording_series.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    measurements = Column(Text, nullable=False)  # JSON object

    series = relationship("RecordingSeries", back_populates="data_points")
```

### 2. Recording Service

```python
# benchmesh-serial-service/src/benchmesh_service/services/recording_service.py

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from benchmesh_service.models.recording import RecordingSeries, DataPoint
from benchmesh_service.database import get_db

class RecordingService:
    def __init__(self):
        self.active_recordings: Dict[int, asyncio.Task] = {}

    async def start_recording(
        self,
        db: Session,
        name: str,
        device_id: str,
        interval_seconds: float,
        parameters: List[str],
        description: Optional[str] = None
    ) -> RecordingSeries:
        """Start a new recording session."""

        # Create series record
        series = RecordingSeries(
            name=name,
            description=description,
            device_id=device_id,
            interval_seconds=interval_seconds,
            parameters=json.dumps(parameters),
            start_time=datetime.utcnow()
        )
        db.add(series)
        db.commit()
        db.refresh(series)

        # Start background recording task
        task = asyncio.create_task(self._recording_loop(series.id, device_id, parameters, interval_seconds))
        self.active_recordings[series.id] = task

        return series

    async def stop_recording(self, db: Session, series_id: int) -> RecordingSeries:
        """Stop an active recording."""

        # Cancel background task
        if series_id in self.active_recordings:
            self.active_recordings[series_id].cancel()
            try:
                await self.active_recordings[series_id]
            except asyncio.CancelledError:
                pass
            del self.active_recordings[series_id]

        # Update series end time
        series = db.query(RecordingSeries).filter(RecordingSeries.id == series_id).first()
        if series:
            series.end_time = datetime.utcnow()
            db.commit()
            db.refresh(series)

        return series

    async def _recording_loop(
        self,
        series_id: int,
        device_id: str,
        parameters: List[str],
        interval_seconds: float
    ):
        """Background task that records data points."""

        from benchmesh_service.serial_manager import serial_manager

        try:
            while True:
                # Get current measurements from device
                measurements = {}

                for param in parameters:
                    try:
                        # Query device for parameter value
                        # Assumes driver has query_<param>() methods
                        method_name = f"query_{param}"
                        if hasattr(serial_manager.get_driver(device_id), method_name):
                            value = getattr(serial_manager.get_driver(device_id), method_name)()
                            measurements[param] = value
                    except Exception as e:
                        print(f"Error reading {param} from {device_id}: {e}")

                # Store data point
                if measurements:
                    db = next(get_db())
                    try:
                        data_point = DataPoint(
                            series_id=series_id,
                            timestamp=datetime.utcnow(),
                            measurements=json.dumps(measurements)
                        )
                        db.add(data_point)

                        # Update series data point count
                        series = db.query(RecordingSeries).filter(RecordingSeries.id == series_id).first()
                        if series:
                            series.data_points_count += 1

                        db.commit()
                    finally:
                        db.close()

                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            # Recording stopped
            pass
        except Exception as e:
            print(f"Recording error for series {series_id}: {e}")

# Global instance
recording_service = RecordingService()
```

### 3. API Endpoints

```python
# benchmesh-serial-service/src/benchmesh_service/api_recording.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
import csv
import io

from benchmesh_service.database import get_db
from benchmesh_service.models.recording import RecordingSeries, DataPoint
from benchmesh_service.services.recording_service import recording_service

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

class StartRecordingRequest(BaseModel):
    name: str
    description: Optional[str] = None
    device_id: str
    interval_seconds: float
    parameters: List[str]

@router.post("/start")
async def start_recording(request: StartRecordingRequest, db: Session = Depends(get_db)):
    """Start a new recording session."""
    try:
        series = await recording_service.start_recording(
            db=db,
            name=request.name,
            device_id=request.device_id,
            interval_seconds=request.interval_seconds,
            parameters=request.parameters,
            description=request.description
        )
        return {
            "series_id": series.id,
            "name": series.name,
            "status": "recording"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{series_id}/stop")
async def stop_recording(series_id: int, db: Session = Depends(get_db)):
    """Stop an active recording."""
    series = await recording_service.stop_recording(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    return {
        "series_id": series.id,
        "status": "stopped",
        "data_points_count": series.data_points_count,
        "duration_seconds": (series.end_time - series.start_time).total_seconds() if series.end_time else 0
    }

@router.get("")
async def list_recordings(db: Session = Depends(get_db)):
    """List all recording series."""
    series_list = db.query(RecordingSeries).order_by(RecordingSeries.start_time.desc()).all()

    return {
        "series": [
            {
                "id": s.id,
                "name": s.name,
                "device_id": s.device_id,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "data_points_count": s.data_points_count,
                "status": "recording" if s.end_time is None else "completed"
            }
            for s in series_list
        ]
    }

@router.get("/{series_id}")
async def get_recording(series_id: int, db: Session = Depends(get_db)):
    """Get recording series details."""
    series = db.query(RecordingSeries).filter(RecordingSeries.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    return {
        "id": series.id,
        "name": series.name,
        "description": series.description,
        "device_id": series.device_id,
        "interval_seconds": series.interval_seconds,
        "parameters": json.loads(series.parameters),
        "start_time": series.start_time.isoformat(),
        "end_time": series.end_time.isoformat() if series.end_time else None,
        "data_points_count": series.data_points_count
    }

@router.delete("/{series_id}")
async def delete_recording(series_id: int, db: Session = Depends(get_db)):
    """Delete a recording series and all its data points."""
    series = db.query(RecordingSeries).filter(RecordingSeries.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Stop if still recording
    if series.end_time is None:
        await recording_service.stop_recording(db, series_id)

    db.delete(series)
    db.commit()

    return {"status": "deleted", "series_id": series_id}

@router.get("/{series_id}/data")
async def get_data_points(
    series_id: int,
    offset: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Get data points for a recording series."""
    series = db.query(RecordingSeries).filter(RecordingSeries.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    points = db.query(DataPoint).filter(
        DataPoint.series_id == series_id
    ).order_by(DataPoint.timestamp).offset(offset).limit(limit).all()

    data = []
    for point in points:
        measurements = json.loads(point.measurements)
        data.append({
            "timestamp": point.timestamp.isoformat(),
            **measurements
        })

    return {
        "series_id": series_id,
        "total_points": series.data_points_count,
        "offset": offset,
        "limit": limit,
        "data": data
    }

@router.get("/{series_id}/export/csv")
async def export_to_csv(series_id: int, db: Session = Depends(get_db)):
    """Export recording data to CSV."""
    series = db.query(RecordingSeries).filter(RecordingSeries.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Get all data points
    points = db.query(DataPoint).filter(
        DataPoint.series_id == series_id
    ).order_by(DataPoint.timestamp).all()

    # Create CSV in memory
    output = io.StringIO()

    if points:
        # Get parameter names from first point
        first_measurements = json.loads(points[0].measurements)
        fieldnames = ["timestamp"] + list(first_measurements.keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for point in points:
            measurements = json.loads(point.measurements)
            row = {
                "timestamp": point.timestamp.isoformat(),
                **measurements
            }
            writer.writerow(row)

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={series.name.replace(' ', '-').lower()}.csv"
        }
    )

@router.get("/active")
async def get_active_recordings(db: Session = Depends(get_db)):
    """Get currently active recordings."""
    active = db.query(RecordingSeries).filter(RecordingSeries.end_time == None).all()

    return {
        "active": [
            {
                "series_id": s.id,
                "name": s.name,
                "device_id": s.device_id,
                "started_at": s.start_time.isoformat(),
                "duration_seconds": (datetime.utcnow() - s.start_time).total_seconds(),
                "data_points_count": s.data_points_count
            }
            for s in active
        ]
    }
```

## Frontend Implementation

### 1. Recording Context/Hook

```typescript
// frontend/src/hooks/useRecording.ts

import { useState, useEffect } from 'react';
import axios from 'axios';

export interface RecordingSeries {
  id: number;
  name: string;
  device_id: string;
  start_time: string;
  end_time?: string;
  data_points_count: number;
  status: 'recording' | 'completed';
}

export interface StartRecordingParams {
  name: string;
  description?: string;
  device_id: string;
  interval_seconds: number;
  parameters: string[];
}

export const useRecording = () => {
  const [series, setSeries] = useState<RecordingSeries[]>([]);
  const [activeSeries, setActiveSeries] = useState<RecordingSeries[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSeries = async () => {
    try {
      const response = await axios.get('/api/recordings');
      setSeries(response.data.series);
    } catch (error) {
      console.error('Error fetching recordings:', error);
    }
  };

  const fetchActive = async () => {
    try {
      const response = await axios.get('/api/recordings/active');
      setActiveSeries(response.data.active);
    } catch (error) {
      console.error('Error fetching active recordings:', error);
    }
  };

  const startRecording = async (params: StartRecordingParams) => {
    setLoading(true);
    try {
      await axios.post('/api/recordings/start', params);
      await fetchSeries();
      await fetchActive();
    } catch (error) {
      console.error('Error starting recording:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const stopRecording = async (seriesId: number) => {
    setLoading(true);
    try {
      await axios.post(`/api/recordings/${seriesId}/stop`);
      await fetchSeries();
      await fetchActive();
    } catch (error) {
      console.error('Error stopping recording:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const deleteRecording = async (seriesId: number) => {
    setLoading(true);
    try {
      await axios.delete(`/api/recordings/${seriesId}`);
      await fetchSeries();
    } catch (error) {
      console.error('Error deleting recording:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const exportToCsv = async (seriesId: number, seriesName: string) => {
    try {
      const response = await axios.get(`/api/recordings/${seriesId}/export/csv`, {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${seriesName}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error exporting to CSV:', error);
      throw error;
    }
  };

  useEffect(() => {
    fetchSeries();
    fetchActive();

    // Poll active recordings every 5 seconds
    const interval = setInterval(fetchActive, 5000);
    return () => clearInterval(interval);
  }, []);

  return {
    series,
    activeSeries,
    loading,
    startRecording,
    stopRecording,
    deleteRecording,
    exportToCsv,
    refreshSeries: fetchSeries
  };
};
```

### 2. Recording Control Component

```typescript
// frontend/src/components/RecordingControl.tsx

import React, { useState } from 'react';
import { useRecording } from '../hooks/useRecording';

interface RecordingControlProps {
  deviceId: string;
  deviceName: string;
  availableParameters: string[];
}

export const RecordingControl: React.FC<RecordingControlProps> = ({
  deviceId,
  deviceName,
  availableParameters
}) => {
  const { activeSeries, startRecording, stopRecording } = useRecording();
  const [showDialog, setShowDialog] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [interval, setInterval] = useState(1.0);
  const [selectedParams, setSelectedParams] = useState<string[]>([]);

  const activeForDevice = activeSeries.find(s => s.device_id === deviceId);

  const handleStart = async () => {
    try {
      await startRecording({
        name,
        description,
        device_id: deviceId,
        interval_seconds: interval,
        parameters: selectedParams
      });
      setShowDialog(false);
      setName('');
      setDescription('');
      setSelectedParams([]);
    } catch (error) {
      alert('Failed to start recording');
    }
  };

  const handleStop = async () => {
    if (activeForDevice && confirm('Stop recording?')) {
      await stopRecording(activeForDevice.series_id);
    }
  };

  if (activeForDevice) {
    return (
      <div className="recording-active">
        <div className="recording-indicator">
          <span className="red-dot">●</span> Recording
        </div>
        <div className="recording-info">
          <strong>{activeForDevice.name}</strong>
          <span>{activeForDevice.data_points_count} points</span>
        </div>
        <button onClick={handleStop}>Stop Recording</button>
      </div>
    );
  }

  return (
    <>
      <button onClick={() => setShowDialog(true)}>
        Start Recording
      </button>

      {showDialog && (
        <div className="dialog-overlay">
          <div className="dialog">
            <h3>Start Recording - {deviceName}</h3>

            <label>
              Recording Name:
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Battery Test 1"
              />
            </label>

            <label>
              Description (optional):
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Testing discharge curve..."
              />
            </label>

            <label>
              Recording Interval (seconds):
              <input
                type="number"
                value={interval}
                onChange={e => setInterval(parseFloat(e.target.value))}
                min="0.1"
                step="0.1"
              />
            </label>

            <label>Parameters to Record:</label>
            <div className="parameter-checkboxes">
              {availableParameters.map(param => (
                <label key={param}>
                  <input
                    type="checkbox"
                    checked={selectedParams.includes(param)}
                    onChange={e => {
                      if (e.target.checked) {
                        setSelectedParams([...selectedParams, param]);
                      } else {
                        setSelectedParams(selectedParams.filter(p => p !== param));
                      }
                    }}
                  />
                  {param}
                </label>
              ))}
            </div>

            <div className="dialog-actions">
              <button onClick={() => setShowDialog(false)}>Cancel</button>
              <button
                onClick={handleStart}
                disabled={!name || selectedParams.length === 0}
              >
                Start Recording
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
```

### 3. Recordings Management Page

```typescript
// frontend/src/pages/RecordingsPage.tsx

import React, { useState } from 'react';
import { useRecording } from '../hooks/useRecording';

export const RecordingsPage: React.FC = () => {
  const { series, loading, deleteRecording, exportToCsv } = useRecording();
  const [filter, setFilter] = useState<'all' | 'recording' | 'completed'>('all');

  const filteredSeries = series.filter(s => {
    if (filter === 'all') return true;
    return s.status === filter;
  });

  const handleDelete = async (seriesId: number, seriesName: string) => {
    if (confirm(`Delete recording "${seriesName}"?`)) {
      await deleteRecording(seriesId);
    }
  };

  const handleExport = async (seriesId: number, seriesName: string) => {
    await exportToCsv(seriesId, seriesName);
  };

  return (
    <div className="recordings-page">
      <header>
        <h1>Data Recordings</h1>
        <div className="filter-buttons">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={filter === 'recording' ? 'active' : ''}
            onClick={() => setFilter('recording')}
          >
            Recording
          </button>
          <button
            className={filter === 'completed' ? 'active' : ''}
            onClick={() => setFilter('completed')}
          >
            Completed
          </button>
        </div>
      </header>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <table className="recordings-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Name</th>
              <th>Device</th>
              <th>Started</th>
              <th>Duration</th>
              <th>Data Points</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredSeries.map(s => (
              <tr key={s.id}>
                <td>
                  {s.status === 'recording' ? (
                    <span className="status-recording">● Recording</span>
                  ) : (
                    <span className="status-completed">✓ Completed</span>
                  )}
                </td>
                <td><strong>{s.name}</strong></td>
                <td>{s.device_id}</td>
                <td>{new Date(s.start_time).toLocaleString()}</td>
                <td>
                  {s.end_time
                    ? formatDuration(
                        new Date(s.end_time).getTime() - new Date(s.start_time).getTime()
                      )
                    : 'Ongoing'}
                </td>
                <td>{s.data_points_count.toLocaleString()}</td>
                <td>
                  <button
                    onClick={() => handleExport(s.id, s.name)}
                    title="Export to CSV"
                  >
                    ⬇ Export
                  </button>
                  <button
                    onClick={() => handleDelete(s.id, s.name)}
                    title="Delete recording"
                    className="delete-button"
                  >
                    🗑 Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {filteredSeries.length === 0 && !loading && (
        <div className="empty-state">
          <p>No recordings yet.</p>
          <p>Start a recording from the device dashboard.</p>
        </div>
      )}
    </div>
  );
};

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}
```

## Real-Time Chart Component (ECharts)

### Installation

```bash
cd benchmesh-serial-service/frontend
npm install echarts echarts-for-react
```

### LiveRecordingChart Component

```typescript
// frontend/src/components/LiveRecordingChart.tsx

import React, { useEffect, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { EChartsOption } from 'echarts';

interface Channel {
  device_id: string;
  parameter: string;
  label: string;
}

interface DataPoint {
  timestamp: string;
  measurements: Record<string, number>;
}

interface LiveRecordingChartProps {
  seriesId: number;
  channels: Channel[];
  maxDataPoints?: number;  // Keep last N points in memory
}

export const LiveRecordingChart: React.FC<LiveRecordingChartProps> = ({
  seriesId,
  channels,
  maxDataPoints = 1000
}) => {
  const [data, setData] = useState<DataPoint[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const chartRef = useRef<any>(null);

  // Group channels by unit for Y-axis assignment
  const channelsByUnit = channels.reduce((acc, channel) => {
    // Infer unit from parameter name (customize as needed)
    const unit = getUnitForParameter(channel.parameter);
    if (!acc[unit]) acc[unit] = [];
    acc[unit].push(channel);
    return acc;
  }, {} as Record<string, Channel[]>);

  useEffect(() => {
    // Connect to WebSocket for live updates
    const ws = new WebSocket(`ws://localhost:57666/ws/recordings/${seriesId}`);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'data_point') {
        setData(prevData => {
          const newData = [...prevData, {
            timestamp: message.timestamp,
            measurements: message.measurements
          }];

          // Keep only last N points
          if (newData.length > maxDataPoints) {
            return newData.slice(-maxDataPoints);
          }
          return newData;
        });
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [seriesId, maxDataPoints]);

  // Generate ECharts option
  const option: EChartsOption = {
    title: {
      text: 'Live Recording',
      textStyle: {
        color: '#fff'
      }
    },
    backgroundColor: '#1a1a1a',
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#333',
      textStyle: {
        color: '#fff'
      }
    },
    legend: {
      data: channels.map(ch => ch.label),
      textStyle: {
        color: '#fff'
      },
      top: 40
    },
    grid: {
      left: '3%',
      right: '10%',
      bottom: '10%',
      containLabel: true
    },
    toolbox: {
      feature: {
        saveAsImage: {
          title: 'Save',
          pixelRatio: 2
        },
        dataZoom: {
          yAxisIndex: 'none',
          title: {
            zoom: 'Zoom',
            back: 'Reset'
          }
        },
        restore: {
          title: 'Restore'
        }
      },
      iconStyle: {
        borderColor: '#fff'
      }
    },
    xAxis: {
      type: 'time',
      boundaryGap: false,
      axisLine: {
        lineStyle: {
          color: '#666'
        }
      },
      axisLabel: {
        color: '#999',
        formatter: (value: number) => {
          const date = new Date(value);
          return date.toLocaleTimeString();
        }
      }
    },
    // Create Y-axes for different units
    yAxis: Object.keys(channelsByUnit).map((unit, index) => ({
      type: 'value',
      name: unit,
      position: index === 0 ? 'left' : 'right',
      offset: index > 1 ? (index - 1) * 60 : 0,
      axisLine: {
        show: true,
        lineStyle: {
          color: getColorForUnit(unit)
        }
      },
      axisLabel: {
        color: '#999',
        formatter: `{value} ${unit}`
      },
      splitLine: {
        lineStyle: {
          color: '#333'
        }
      }
    })),
    // Create series for each channel
    series: channels.map(channel => {
      const unit = getUnitForParameter(channel.parameter);
      const yAxisIndex = Object.keys(channelsByUnit).indexOf(unit);
      const key = `${channel.device_id}.${channel.parameter}`;

      return {
        name: channel.label,
        type: 'line',
        yAxisIndex: yAxisIndex,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2
        },
        data: data.map(point => [
          new Date(point.timestamp).getTime(),
          point.measurements[key]
        ])
      };
    }),
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        start: 0,
        end: 100,
        textStyle: {
          color: '#fff'
        }
      }
    ]
  };

  return (
    <div className="live-recording-chart">
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: '600px', width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
        theme="dark"
      />
    </div>
  );
};

// Helper functions
function getUnitForParameter(parameter: string): string {
  const units: Record<string, string> = {
    'voltage': 'V',
    'current': 'A',
    'power': 'W',
    'resistance': 'Ω',
    'temperature': '°C',
    'frequency': 'Hz'
  };
  return units[parameter.toLowerCase()] || '';
}

function getColorForUnit(unit: string): string {
  const colors: Record<string, string> = {
    'V': '#5470c6',
    'A': '#91cc75',
    'W': '#fac858',
    'Ω': '#ee6666',
    '°C': '#73c0de',
    'Hz': '#3ba272'
  };
  return colors[unit] || '#999';
}
```

### Recording Detail Page with Chart

```typescript
// frontend/src/pages/RecordingDetailPage.tsx

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { LiveRecordingChart } from '../components/LiveRecordingChart';
import axios from 'axios';

interface RecordingSeries {
  id: number;
  name: string;
  description: string;
  interval_seconds: number;
  channels: Array<{
    device_id: string;
    parameter: string;
    label: string;
  }>;
  start_time: string;
  end_time?: string;
  paused_at?: string;
  data_points_count: number;
}

export const RecordingDetailPage: React.FC = () => {
  const { seriesId } = useParams<{ seriesId: string }>();
  const [series, setSeries] = useState<RecordingSeries | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    fetchSeries();
  }, [seriesId]);

  const fetchSeries = async () => {
    try {
      const response = await axios.get(`/api/recordings/${seriesId}`);
      const data = response.data;
      setSeries(data);
      setIsPaused(!!data.paused_at);
      setIsRecording(!data.end_time);
    } catch (error) {
      console.error('Error fetching series:', error);
    }
  };

  const handlePause = async () => {
    try {
      await axios.post(`/api/recordings/${seriesId}/pause`);
      setIsPaused(true);
    } catch (error) {
      console.error('Error pausing recording:', error);
    }
  };

  const handleResume = async () => {
    try {
      await axios.post(`/api/recordings/${seriesId}/resume`);
      setIsPaused(false);
    } catch (error) {
      console.error('Error resuming recording:', error);
    }
  };

  const handleStop = async () => {
    if (confirm('Stop recording? This cannot be undone.')) {
      try {
        await axios.post(`/api/recordings/${seriesId}/stop`);
        setIsRecording(false);
      } catch (error) {
        console.error('Error stopping recording:', error);
      }
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get(`/api/recordings/${seriesId}/export/csv`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${series?.name || 'recording'}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error exporting:', error);
    }
  };

  if (!series) {
    return <div>Loading...</div>;
  }

  return (
    <div className="recording-detail-page">
      <header className="recording-header">
        <div className="recording-info">
          <h1>{series.name}</h1>
          {series.description && <p>{series.description}</p>}
          <div className="recording-meta">
            <span>Started: {new Date(series.start_time).toLocaleString()}</span>
            <span>Interval: {series.interval_seconds}s</span>
            <span>Data Points: {series.data_points_count.toLocaleString()}</span>
            {isRecording && (
              <span className="status-badge recording">
                {isPaused ? '⏸ Paused' : '● Recording'}
              </span>
            )}
          </div>
        </div>

        <div className="recording-controls">
          {isRecording && !isPaused && (
            <button onClick={handlePause} className="btn-pause">
              ⏸ Pause
            </button>
          )}
          {isRecording && isPaused && (
            <button onClick={handleResume} className="btn-resume">
              ▶ Resume
            </button>
          )}
          {isRecording && (
            <button onClick={handleStop} className="btn-stop">
              ⏹ Stop
            </button>
          )}
          <button onClick={handleExport} className="btn-export">
            ⬇ Export CSV
          </button>
        </div>
      </header>

      <div className="chart-container">
        {isRecording ? (
          <LiveRecordingChart
            seriesId={parseInt(seriesId!)}
            channels={series.channels}
            maxDataPoints={1000}
          />
        ) : (
          <div className="historical-chart">
            {/* Load all data and render static chart */}
            <p>Recording completed. Loading historical data...</p>
          </div>
        )}
      </div>

      <div className="channels-info">
        <h3>Recording Channels</h3>
        <table>
          <thead>
            <tr>
              <th>Device</th>
              <th>Parameter</th>
              <th>Label</th>
            </tr>
          </thead>
          <tbody>
            {series.channels.map((ch, idx) => (
              <tr key={idx}>
                <td>{ch.device_id}</td>
                <td>{ch.parameter}</td>
                <td>{ch.label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
```

## Implementation Phases

### Phase 1: Backend Foundation (1 day)
1. Add SQLAlchemy to requirements.txt
2. Create database models (multi-device support)
3. Implement database initialization
4. Create basic recording service with pause/resume
5. Add API endpoints (start/pause/resume/stop)
6. Add WebSocket endpoint for live data streaming

### Phase 2: Backend Recording Logic (1 day)
1. Multi-device data collection loop
2. Data point storage with proper indexing
3. Pause/resume state management
4. Active recording status tracking
5. CSV export with all channels

### Phase 3: Real-Time Charts (1 day)
1. Install echarts and echarts-for-react
2. Create LiveRecordingChart component
3. WebSocket integration for live updates
4. Multi-axis support for different units
5. Chart theming and styling
6. Export chart as image

### Phase 4: Recording Management UI (1 day)
1. Start recording dialog (multi-device channel picker)
2. Recording detail page with live chart
3. Recordings list page
4. Pause/Resume/Stop controls
5. CSV export button
6. Delete recording functionality

### Phase 5: Polish & Testing (1 day)
1. Error handling and edge cases
2. Performance testing with long recordings
3. WebSocket reconnection logic
4. Chart performance optimization
5. UI polish and responsive design
6. Documentation

## Testing Strategy

### Backend Tests
```python
# Test recording start/stop
# Test data point storage
# Test concurrent recordings
# Test CSV export format
# Test deletion cascade
```

### Frontend Tests
```typescript
// Test recording controls
// Test series list rendering
// Test export functionality
// Test delete confirmation
```

### Integration Tests
```bash
# Test full recording workflow
# Test multiple devices recording simultaneously
# Test large dataset handling (10k+ points)
# Test CSV export accuracy
```

## Performance Considerations

1. **Database Indexes**: Already included in schema
2. **Batch Inserts**: Group data points for bulk insert every N seconds
3. **Pagination**: API returns data in pages (1000 points default)
4. **Background Tasks**: Recording runs in separate async task
5. **Database Location**: Store on fast disk (SSD recommended)

## Configuration

Add to `config.yaml`:

```yaml
recording:
  database_path: "./data/recordings.db"  # SQLite database location
  max_series: 100                        # Maximum number of series to keep
  auto_cleanup_days: 90                  # Auto-delete recordings older than N days
  batch_size: 10                         # Insert data points in batches
```

## Next Steps

1. Review and approve this plan
2. Create feature branch: `feature/data-recording`
3. Implement Phase 1 (Backend Foundation)
4. Test with simple recording
5. Implement Phase 2 (Basic Recording)
6. Test with real devices
7. Implement Phase 3 (Frontend UI)
8. Implement Phase 4 (Export & Management)
9. Documentation update
10. User testing

## Key Features Summary

✅ **Multi-Device Recording** - Record from multiple devices in one series
✅ **Pause/Resume** - Full pause and resume support
✅ **Real-Time Charts** - Stunning ECharts visualization with live updates
✅ **WebSocket Streaming** - Live data pushed to frontend
✅ **Multi-Axis Charts** - Different Y-axes for different units
✅ **CSV Export** - Per-series export with all channels
✅ **Manual Deletion** - User controls data retention
✅ **Works Everywhere** - Identical in web and Electron

## Use Case Example

**Battery Discharge Test**:
- Record PSU voltage and current (device psu-1)
- Record actual load voltage from DMM (device dmm-1)
- Record power consumption from electronic load (device ell-1)
- View all 4 parameters in real-time on one chart
- Pause during breaks, resume testing
- Export complete dataset to CSV for analysis

---

**Estimated Implementation Time**: 5 days
**Complexity**: Medium-High
**Dependencies**: SQLAlchemy, ECharts, WebSockets

**Technologies**:
- Backend: Python, FastAPI, SQLAlchemy, SQLite, WebSockets
- Frontend: React, TypeScript, ECharts, echarts-for-react
- Database: SQLite 3

This architecture provides a professional data recording system with stunning visuals that works across all deployment modes and scales well for typical lab use cases (millions of data points).
