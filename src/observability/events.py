"""
Desktop observability event system.

Centralized event tracking for metrics and diagnostics.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import RLock

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types for observability."""
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_PAUSED = "job_paused"
    JOB_RESUMED = "job_resumed"
    JOB_STOPPED = "job_stopped"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    RESOURCE_WARNING = "resource_warning"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    BROWSER_STARTED = "browser_started"
    BROWSER_STOPPED = "browser_stopped"
    NETWORK_REQUEST = "network_request"
    NETWORK_ERROR = "network_error"
    ERROR = "error"
    CUSTOM = "custom"


@dataclass
class ObservabilityEvent:
    """Single observability event."""
    event_type: EventType
    timestamp: datetime
    job_id: Optional[str]
    data: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)


class EventCollector:
    """
    Collects observability events for metrics and diagnostics.

    Thread-safe event collection with circular buffer.
    """

    def __init__(self, max_events: int = 10000):
        """
        Initialize event collector.

        Args:
            max_events: Maximum events to keep in memory
        """
        self.max_events = max_events
        self._lock = RLock()
        self._events: List[ObservabilityEvent] = []
        self._subscribers: List[Callable[[ObservabilityEvent], None]] = []

    def emit(
        self,
        event_type: EventType,
        job_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Emit event.

        Args:
            event_type: Event type
            job_id: Associated job ID
            data: Event data
            tags: Event tags
        """
        event = ObservabilityEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            job_id=job_id,
            data=data or {},
            tags=tags or {}
        )

        with self._lock:
            self._events.append(event)

            # Circular buffer
            if len(self._events) > self.max_events:
                self._events.pop(0)

        # Notify subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"Subscriber error: {e}", exc_info=True)

        logger.debug(f"Event emitted: {event_type}")

    def subscribe(self, callback: Callable[[ObservabilityEvent], None]):
        """Subscribe to events."""
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[ObservabilityEvent], None]):
        """Unsubscribe from events."""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        job_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ObservabilityEvent]:
        """
        Get events with filters.

        Args:
            event_type: Filter by event type
            job_id: Filter by job ID
            limit: Maximum events to return

        Returns:
            Filtered events (most recent first)
        """
        with self._lock:
            filtered = []
            for event in reversed(self._events):
                if event_type and event.event_type != event_type:
                    continue
                if job_id and event.job_id != job_id:
                    continue

                filtered.append(event)

                if len(filtered) >= limit:
                    break

            return filtered

    def get_timeline(self, job_id: str) -> List[ObservabilityEvent]:
        """
        Get event timeline for job.

        Args:
            job_id: Job identifier

        Returns:
            Events in chronological order
        """
        with self._lock:
            return sorted(
                [e for e in self._events if e.job_id == job_id],
                key=lambda e: e.timestamp
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get event statistics."""
        with self._lock:
            by_type = {}
            for event_type in EventType:
                count = len([e for e in self._events if e.event_type == event_type])
                if count > 0:
                    by_type[event_type.value] = count

            return {
                'total_events': len(self._events),
                'by_type': by_type,
                'oldest_event': self._events[0].timestamp.isoformat() if self._events else None,
                'newest_event': self._events[-1].timestamp.isoformat() if self._events else None
            }

    def clear(self):
        """Clear all events."""
        with self._lock:
            self._events.clear()
