"""
Recording API endpoints.

Provides REST API for managing data recordings with pause/resume support.
"""

import json
import csv
import io
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from benchmesh_service.database import get_db
from benchmesh_service.models.recording import RecordingSeries, DataPoint
import benchmesh_service.services.recording_service as recording_service_module
from benchmesh_service.logger import logger


class ChannelConfig(BaseModel):
    """Configuration for a single recording channel."""
    device_id: str
    class_name: str
    channel: int
    method_name: str
    label: Optional[str] = None


class StartRecordingRequest(BaseModel):
    """Request to start a new recording."""
    name: str
    channels: List[ChannelConfig]
    interval_seconds: float
    description: Optional[str] = None


class RecordingResponse(BaseModel):
    """Response for recording operations."""
    series_id: int
    name: str
    status: str
    paused_at: Optional[str] = None


class RecordingDetailsResponse(BaseModel):
    """Detailed recording information."""
    id: int
    name: str
    description: Optional[str]
    interval_seconds: float
    channels: List[dict]
    start_time: str
    end_time: Optional[str]
    paused_at: Optional[str]
    pause_duration_seconds: float
    data_points_count: int


def create_recording_router() -> APIRouter:
    """
    Create and configure the recording API router.

    Returns:
        APIRouter: Configured router
    """
    router = APIRouter(tags=["recordings"])

    @router.post("/start")
    async def start_recording(
        request: StartRecordingRequest,
        db: Session = Depends(get_db)
    ):
        """Start a new recording session."""
        try:
            # Convert channels to dict format
            channels = [ch.model_dump() for ch in request.channels]

            series = await recording_service_module.recording_service.start_recording(
                db=db,
                name=request.name,
                channels=channels,
                interval_seconds=request.interval_seconds,
                description=request.description
            )

            return {
                "series_id": series.id,
                "name": series.name,
                "status": "recording"
            }
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{series_id}/pause")
    async def pause_recording(series_id: int, db: Session = Depends(get_db)):
        """Pause an active recording."""
        try:
            series = await recording_service_module.recording_service.pause_recording(db, series_id)
            if not series:
                raise HTTPException(status_code=404, detail="Recording not found")

            return {
                "series_id": series.id,
                "name": series.name,
                "status": "paused",
                "paused_at": series.paused_at.isoformat() if series.paused_at else None
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error pausing recording: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{series_id}/resume")
    async def resume_recording(series_id: int, db: Session = Depends(get_db)):
        """Resume a paused recording."""
        try:
            series = await recording_service_module.recording_service.resume_recording(db, series_id)
            if not series:
                raise HTTPException(status_code=404, detail="Recording not found")

            return {
                "series_id": series.id,
                "name": series.name,
                "status": "recording",
                "paused_at": None
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error resuming recording: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{series_id}/stop")
    async def stop_recording(series_id: int, db: Session = Depends(get_db)):
        """Stop an active recording."""
        # Check if recording exists first
        series = db.query(RecordingSeries).filter(
            RecordingSeries.id == series_id
        ).first()

        if not series:
            raise HTTPException(status_code=404, detail="Recording not found")

        try:
            series = await recording_service_module.recording_service.stop_recording(db, series_id)

            duration = 0
            if series.end_time and series.start_time:
                duration = (series.end_time - series.start_time).total_seconds()
                # Subtract pause duration
                duration -= series.pause_duration_seconds

            return {
                "series_id": series.id,
                "name": series.name,
                "status": "stopped",
                "data_points_count": series.data_points_count,
                "duration_seconds": duration,
                "pause_duration_seconds": series.pause_duration_seconds
            }
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("")
    async def list_recordings(db: Session = Depends(get_db)):
        """List all recording series."""
        series_list = db.query(RecordingSeries).order_by(
            RecordingSeries.start_time.desc()
        ).all()

        # Calculate total duration for each recording
        recordings = []
        for s in series_list:
            # Calculate total duration (excluding pauses)
            if s.end_time:
                # Recording stopped: use actual duration
                total_duration = (s.end_time - s.start_time).total_seconds() - s.pause_duration_seconds
            else:
                # Recording active: use current time
                total_duration = (datetime.utcnow() - s.start_time).total_seconds() - s.pause_duration_seconds

            recordings.append({
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "interval_seconds": s.interval_seconds,
                "channels": json.loads(s.channels),
                "total_duration_seconds": max(0, total_duration),  # Ensure non-negative
                "pause_duration_seconds": s.pause_duration_seconds,
                "paused_at": s.paused_at.isoformat() if s.paused_at else None,
                "status": "paused" if s.paused_at else ("stopped" if s.end_time else "recording")
            })

        return {"recordings": recordings}

    @router.get("/{series_id}")
    async def get_recording(series_id: int, db: Session = Depends(get_db)):
        """Get details of a specific recording."""
        series = db.query(RecordingSeries).filter(
            RecordingSeries.id == series_id
        ).first()

        if not series:
            raise HTTPException(status_code=404, detail="Recording not found")

        return {
            "id": series.id,
            "name": series.name,
            "description": series.description,
            "interval_seconds": series.interval_seconds,
            "channels": json.loads(series.channels),
            "start_time": series.start_time.isoformat(),
            "end_time": series.end_time.isoformat() if series.end_time else None,
            "paused_at": series.paused_at.isoformat() if series.paused_at else None,
            "pause_duration_seconds": series.pause_duration_seconds,
            "data_points_count": series.data_points_count
        }

    @router.delete("/{series_id}")
    async def delete_recording(series_id: int, db: Session = Depends(get_db)):
        """Delete a recording series and all its data points."""
        series = db.query(RecordingSeries).filter(
            RecordingSeries.id == series_id
        ).first()

        if not series:
            raise HTTPException(status_code=404, detail="Recording not found")

        # Stop recording if active
        if series_id in recording_service_module.recording_service.get_active_recording_ids():
            await recording_service_module.recording_service.stop_recording(db, series_id)

        db.delete(series)
        db.commit()

        logger.info(f"Deleted recording: {series.name} (ID: {series_id})")

        return {
            "status": "deleted",
            "series_id": series_id
        }

    @router.get("/{series_id}/data")
    async def get_recording_data(
        series_id: int,
        offset: int = 0,
        limit: int = 1000,
        db: Session = Depends(get_db)
    ):
        """Get data points for a recording series."""
        series = db.query(RecordingSeries).filter(
            RecordingSeries.id == series_id
        ).first()

        if not series:
            raise HTTPException(status_code=404, detail="Recording not found")

        # Get total count
        total_points = series.data_points_count

        # Get paginated data points
        points = db.query(DataPoint).filter(
            DataPoint.series_id == series_id
        ).order_by(
            DataPoint.timestamp
        ).offset(offset).limit(limit).all()

        # Format data
        data = [
            {
                "timestamp": point.timestamp.isoformat(),
                **json.loads(point.measurements)
            }
            for point in points
        ]

        return {
            "series_id": series_id,
            "total_points": total_points,
            "offset": offset,
            "limit": limit,
            "data": data
        }

    @router.get("/{series_id}/export")
    async def export_recording(series_id: int, db: Session = Depends(get_db)):
        """Export recording data to CSV."""
        series = db.query(RecordingSeries).filter(
            RecordingSeries.id == series_id
        ).first()

        if not series:
            raise HTTPException(status_code=404, detail="Recording not found")

        # Get all data points
        points = db.query(DataPoint).filter(
            DataPoint.series_id == series_id
        ).order_by(DataPoint.timestamp).all()

        # Generate CSV
        output = io.StringIO()

        if points:
            # Get all measurement keys from first point
            first_measurements = json.loads(points[0].measurements)
            fieldnames = ["timestamp"] + sorted(first_measurements.keys())

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for point in points:
                measurements = json.loads(point.measurements)
                row = {"timestamp": point.timestamp.isoformat()}
                row.update(measurements)
                writer.writerow(row)
        else:
            # Empty CSV with just headers
            channels = json.loads(series.channels)
            fieldnames = ["timestamp"] + [
                f"{ch['device_id']}_{ch['class_name']}_{ch['channel']}_{ch['method_name']}" for ch in channels
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

        # Return CSV file
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={series.name.replace(' ', '_')}.csv"
            }
        )

    @router.websocket("/ws/{series_id}")
    async def websocket_endpoint(websocket: WebSocket, series_id: int):
        """WebSocket endpoint for live data streaming."""
        await websocket.accept()

        # Verify series exists
        from benchmesh_service.database import get_db_context
        with get_db_context() as db:
            series = db.query(RecordingSeries).filter(
                RecordingSeries.id == series_id
            ).first()

            if not series:
                await websocket.close(code=1008, reason="Recording not found")
                return

        # Add websocket to recording service
        await recording_service_module.recording_service.add_websocket(series_id, websocket)

        try:
            # Keep connection alive and wait for disconnect
            while True:
                # Receive message (mainly to detect disconnect)
                data = await websocket.receive_text()
                # Echo back for ping/pong
                await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected for series {series_id}")
        except Exception as e:
            logger.error(f"WebSocket error for series {series_id}: {e}")
        finally:
            # Remove websocket from recording service
            await recording_service_module.recording_service.remove_websocket(series_id, websocket)

    return router
