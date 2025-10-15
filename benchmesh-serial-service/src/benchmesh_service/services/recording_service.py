"""
Recording service for data collection with pause/resume support.

This service manages background tasks that collect data from devices at
specified intervals and stores them in the database.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from sqlalchemy.orm import Session
from fastapi import WebSocket

from benchmesh_service.models.recording import RecordingSeries, DataPoint
from benchmesh_service.database import get_db_context
from benchmesh_service.logger import logger


class RecordingService:
    """
    Service for managing data recording sessions.

    Handles starting, pausing, resuming, and stopping recordings with
    multi-device support.
    """

    def __init__(self, serial_manager=None):
        """
        Initialize recording service.

        Args:
            serial_manager: SerialManager instance for device access
        """
        self.serial_manager = serial_manager
        self.active_recordings: Dict[int, Dict[str, Any]] = {}
        self.websocket_connections: Dict[int, Set[WebSocket]] = {}  # series_id -> set of websockets

    async def start_recording(
        self,
        db: Session,
        name: str,
        channels: List[Dict[str, str]],
        interval_seconds: float,
        description: Optional[str] = None
    ) -> RecordingSeries:
        """
        Start a new recording session.

        Args:
            db: Database session
            name: Unique name for the recording
            channels: List of channel definitions with device_id, class_name, channel, method_name, label
            interval_seconds: Data collection interval in seconds
            description: Optional description

        Returns:
            RecordingSeries: Created series record

        Raises:
            IntegrityError: If name already exists
        """
        # Create series record
        series = RecordingSeries(
            name=name,
            description=description,
            interval_seconds=interval_seconds,
            channels=json.dumps(channels),
            start_time=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(series)
        db.commit()
        db.refresh(series)

        logger.info(f"Started recording: {name} (ID: {series.id})")

        # Start background recording task
        task = asyncio.create_task(
            self._recording_loop(series.id, channels, interval_seconds)
        )

        self.active_recordings[series.id] = {
            "task": task,
            "paused": False,
            "channels": channels,
            "interval_seconds": interval_seconds
        }

        return series

    async def pause_recording(self, db: Session, series_id: int) -> RecordingSeries:
        """
        Pause an active recording.

        Args:
            db: Database session
            series_id: ID of series to pause

        Returns:
            RecordingSeries: Updated series record
        """
        if series_id not in self.active_recordings:
            raise ValueError(f"Recording {series_id} is not active")

        # Mark as paused (recording loop will check this flag)
        self.active_recordings[series_id]["paused"] = True

        # Update database
        series = db.query(RecordingSeries).filter(
            RecordingSeries.id == series_id
        ).first()

        if series:
            series.paused_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            db.refresh(series)
            logger.info(f"Paused recording: {series.name} (ID: {series_id})")

        return series

    async def resume_recording(self, db: Session, series_id: int) -> RecordingSeries:
        """
        Resume a paused recording.

        Args:
            db: Database session
            series_id: ID of series to resume

        Returns:
            RecordingSeries: Updated series record
        """
        if series_id not in self.active_recordings:
            raise ValueError(f"Recording {series_id} is not active")

        # Calculate pause duration
        series = db.query(RecordingSeries).filter(
            RecordingSeries.id == series_id
        ).first()

        if series and series.paused_at:
            pause_duration = (datetime.now(timezone.utc).replace(tzinfo=None) - series.paused_at).total_seconds()
            series.pause_duration_seconds += pause_duration
            series.paused_at = None
            db.commit()
            db.refresh(series)
            logger.info(
                f"Resumed recording: {series.name} (ID: {series_id}), "
                f"paused for {pause_duration:.1f}s"
            )

        # Resume recording loop
        self.active_recordings[series_id]["paused"] = False

        return series

    async def stop_recording(self, db: Session, series_id: int) -> RecordingSeries:
        """
        Stop an active recording.

        Args:
            db: Database session
            series_id: ID of series to stop

        Returns:
            RecordingSeries: Updated series record
        """
        # Cancel background task
        if series_id in self.active_recordings:
            recording_info = self.active_recordings[series_id]
            recording_info["task"].cancel()

            try:
                await recording_info["task"]
            except asyncio.CancelledError:
                pass

            del self.active_recordings[series_id]

        # Update series end time
        series = db.query(RecordingSeries).filter(
            RecordingSeries.id == series_id
        ).first()

        if series:
            series.end_time = datetime.now(timezone.utc).replace(tzinfo=None)
            # If still paused, add final pause duration
            if series.paused_at:
                pause_duration = (datetime.now(timezone.utc).replace(tzinfo=None) - series.paused_at).total_seconds()
                series.pause_duration_seconds += pause_duration
                series.paused_at = None
            db.commit()
            db.refresh(series)
            logger.info(f"Stopped recording: {series.name} (ID: {series_id})")

        return series

    def get_active_recording_ids(self) -> List[int]:
        """
        Get list of active recording IDs.

        Returns:
            List[int]: List of active series IDs
        """
        return list(self.active_recordings.keys())

    async def add_websocket(self, series_id: int, websocket: WebSocket):
        """
        Add a WebSocket connection for a series.

        Args:
            series_id: ID of recording series
            websocket: WebSocket connection
        """
        if series_id not in self.websocket_connections:
            self.websocket_connections[series_id] = set()
        self.websocket_connections[series_id].add(websocket)
        logger.debug(f"Added WebSocket for series {series_id}")

    async def remove_websocket(self, series_id: int, websocket: WebSocket):
        """
        Remove a WebSocket connection for a series.

        Args:
            series_id: ID of recording series
            websocket: WebSocket connection
        """
        if series_id in self.websocket_connections:
            self.websocket_connections[series_id].discard(websocket)
            if not self.websocket_connections[series_id]:
                del self.websocket_connections[series_id]
            logger.debug(f"Removed WebSocket for series {series_id}")

    async def broadcast_data_point(
        self,
        series_id: int,
        timestamp: datetime,
        measurements: Dict[str, Any]
    ):
        """
        Broadcast a new data point to all connected WebSockets.

        Args:
            series_id: ID of recording series
            timestamp: Timestamp of data point
            measurements: Measurement data
        """
        if series_id not in self.websocket_connections:
            return

        message = {
            "type": "data_point",
            "series_id": series_id,
            "timestamp": timestamp.isoformat(),
            "measurements": measurements
        }

        # Send to all connected websockets
        disconnected = set()
        for websocket in self.websocket_connections[series_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to websocket: {e}")
                disconnected.add(websocket)

        # Remove disconnected websockets
        for websocket in disconnected:
            await self.remove_websocket(series_id, websocket)

    async def _recording_loop(
        self,
        series_id: int,
        channels: List[Dict[str, str]],
        interval_seconds: float
    ):
        """
        Background task that records data points.

        Args:
            series_id: ID of recording series
            channels: List of channel definitions
            interval_seconds: Collection interval in seconds
        """
        logger.info(f"Recording loop started for series {series_id} with {len(channels)} channels, interval={interval_seconds}s")
        logger.info(f"Channels: {channels}")

        try:
            while True:
                # Check if paused
                if series_id in self.active_recordings:
                    if self.active_recordings[series_id]["paused"]:
                        await asyncio.sleep(0.1)  # Check pause state frequently
                        continue

                # Collect measurements from all channels
                measurements = {}

                logger.debug(f"[Series {series_id}] Starting data collection cycle...")

                for channel in channels:
                    device_id = channel["device_id"]
                    class_name = channel["class_name"]
                    channel_num = channel["channel"]
                    method_name = channel["method_name"]

                    # Key format matches frontend: device_id_class_name_channel_method_name
                    key = f"{device_id}_{class_name}_{channel_num}_{method_name}"

                    try:
                        # Get driver and query method
                        if not self.serial_manager:
                            logger.error(f"[Series {series_id}] No serial_manager available!")
                            continue

                        driver = self.serial_manager.connections.get(device_id)
                        if not driver:
                            logger.warning(f"[Series {series_id}] Device {device_id} not connected")
                            continue

                        query_method = f"query_{method_name}"
                        if not hasattr(driver, query_method):
                            logger.error(f"[Series {series_id}] Device {device_id} does not have method '{query_method}'. Available methods: {[m for m in dir(driver) if m.startswith('query_')]}")
                            continue

                        # Call the method with channel number as parameter
                        logger.debug(f"[Series {series_id}] Calling {device_id}.{query_method}({channel_num})")
                        value = getattr(driver, query_method)(channel_num)
                        measurements[key] = value
                        logger.info(f"[Series {series_id}] ✓ {device_id}.{query_method}({channel_num}) = {value}")

                    except Exception as e:
                        logger.error(
                            f"[Series {series_id}] Error reading {method_name} from {device_id} channel {channel_num}: {e}",
                            exc_info=True
                        )

                # Store data point if we got any measurements
                if measurements:
                    logger.info(f"[Series {series_id}] Collected {len(measurements)} measurements: {measurements}")
                    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

                    with get_db_context() as db:
                        try:
                            data_point = DataPoint(
                                series_id=series_id,
                                timestamp=timestamp,
                                measurements=json.dumps(measurements)
                            )
                            db.add(data_point)

                            # Update series data point count
                            series = db.query(RecordingSeries).filter(
                                RecordingSeries.id == series_id
                            ).first()
                            if series:
                                series.data_points_count += 1

                            db.commit()
                        except Exception as e:
                            logger.error(
                                f"Error storing data point for series {series_id}: {e}"
                            )

                    # Broadcast to WebSocket clients
                    await self.broadcast_data_point(series_id, timestamp, measurements)

                # Wait for next interval
                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            # Recording stopped
            logger.debug(f"Recording loop cancelled for series {series_id}")
        except Exception as e:
            logger.error(f"Recording error for series {series_id}: {e}")


# Global instance (will be initialized with serial_manager in api.py)
recording_service: Optional[RecordingService] = None


def init_recording_service(serial_manager):
    """
    Initialize global recording service instance.

    Args:
        serial_manager: SerialManager instance
    """
    global recording_service
    recording_service = RecordingService(serial_manager=serial_manager)
    return recording_service
