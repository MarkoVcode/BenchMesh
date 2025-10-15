"""
Priority Queue System for Device Requests

This module implements a priority-based request queue for device operations,
allowing API requests to preempt background polling operations.

Priority Levels:
- HIGH (1): User-triggered API requests
- LOW (10): Background polling operations

The queue ensures API requests are processed before polling requests,
minimizing user-perceived latency while maintaining regular device polling.
"""

import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from queue import PriorityQueue, Empty
from typing import Any, Callable, Optional


class Priority(IntEnum):
    """
    Priority levels for device requests.

    Lower numeric values = higher priority.
    """
    HIGH = 1    # API requests (user-triggered, interactive)
    LOW = 10    # Background polling (monitoring, updates)


@dataclass(order=True)
class PriorityRequest:
    """
    A request with priority for queue ordering.

    Requests are ordered first by priority (lower = higher), then by timestamp (FIFO).
    The request payload is excluded from comparison to avoid type comparison errors.

    Attributes:
        priority: Priority level of the request
        timestamp: When the request was created (for FIFO within same priority)
        request: The actual request payload (excluded from comparison)
    """
    priority: Priority
    timestamp: float = field(compare=True)
    request: Any = field(compare=False)


@dataclass
class PollRequest:
    """
    Request to poll device status.

    Attributes:
        device_id: ID of device to poll
        now: Timestamp when poll was requested
    """
    type: str = "poll"
    device_id: str = ""
    now: float = 0.0


@dataclass
class ApiRequest:
    """
    Request to execute API call on device.

    Attributes:
        type: Request type identifier ("api")
        device_id: ID of device to query
        method: Driver method name to call
        args: Positional arguments for method
        kwargs: Keyword arguments for method
        result_callback: Callback to invoke with result or exception
    """
    type: str = "api"
    device_id: str = ""
    method: str = ""
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    result_callback: Optional[Callable] = None


class DeviceRequestQueue:
    """
    Priority queue for a single device's requests.

    Manages the queue of pending requests for a device, ensuring high-priority
    API requests are processed before low-priority polling requests.

    Thread-safe for concurrent enqueue/dequeue operations.

    Attributes:
        device_id: ID of the device this queue serves
        queue: Priority queue of pending requests
        current_request: Request currently being executed (if any)
        lock: Lock for thread-safe access to current_request
    """

    def __init__(self, device_id: str):
        """
        Initialize queue for a device.

        Args:
            device_id: Unique identifier for the device
        """
        self.device_id = device_id
        self.queue: PriorityQueue[PriorityRequest] = PriorityQueue()
        self.current_request: Optional[PriorityRequest] = None
        self.lock = threading.Lock()

    def enqueue(self, request: Any, priority: Priority) -> None:
        """
        Add a request to the queue with specified priority.

        Args:
            request: Request object (PollRequest, ApiRequest, or other)
            priority: Priority level for the request
        """
        pr = PriorityRequest(
            priority=priority,
            timestamp=time.time(),
            request=request
        )
        self.queue.put(pr)

    def dequeue(self, timeout: Optional[float] = None) -> Optional[PriorityRequest]:
        """
        Get the next highest-priority request from queue.

        Blocks until a request is available or timeout expires.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            Next request, or None if timeout expires
        """
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            return None

    def try_dequeue(self) -> Optional[PriorityRequest]:
        """
        Attempt to get next request without blocking.

        Returns:
            Next request if available, None otherwise
        """
        try:
            return self.queue.get_nowait()
        except Empty:
            return None

    def qsize(self) -> int:
        """
        Get approximate queue size.

        Note: This is approximate and may not be accurate in concurrent scenarios.

        Returns:
            Approximate number of pending requests
        """
        return self.queue.qsize()

    def set_current_request(self, request: Optional[PriorityRequest]) -> None:
        """
        Set the currently executing request (thread-safe).

        Args:
            request: Request being executed, or None when complete
        """
        with self.lock:
            self.current_request = request

    def get_current_request(self) -> Optional[PriorityRequest]:
        """
        Get the currently executing request (thread-safe).

        Returns:
            Request being executed, or None if idle
        """
        with self.lock:
            return self.current_request
