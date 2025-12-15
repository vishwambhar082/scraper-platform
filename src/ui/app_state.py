"""
Application state store for desktop UI.

Centralized state management with event-driven updates.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import RLock

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class JobState:
    """State for a single job."""
    job_id: str
    pipeline_id: str
    source: str
    status: JobStatus
    progress: float = 0.0
    current_step: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemResources:
    """System resource usage."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    browser_count: int
    timestamp: datetime


class AppState:
    """
    Application state store.

    Thread-safe centralized state with event notifications.
    """

    def __init__(self):
        """Initialize app state."""
        self._lock = RLock()
        self._jobs: Dict[str, JobState] = {}
        self._resources: Optional[SystemResources] = None
        self._errors: List[Dict[str, Any]] = []
        self._subscribers: List[Callable[[str, Any], None]] = []

    def subscribe(self, callback: Callable[[str, Any], None]):
        """
        Subscribe to state changes.

        Args:
            callback: Function(event_type, data) called on state changes
        """
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, Any], None]):
        """Unsubscribe from state changes."""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def _notify(self, event_type: str, data: Any):
        """Notify all subscribers of state change."""
        with self._lock:
            subscribers = self._subscribers.copy()

        for callback in subscribers:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Subscriber error: {e}", exc_info=True)

    # Job state management

    def add_job(self, job_state: JobState):
        """Add new job to state."""
        with self._lock:
            self._jobs[job_state.job_id] = job_state
            self._notify('job_added', job_state)
            logger.debug(f"Job added: {job_state.job_id}")

    def update_job(self, job_id: str, **updates):
        """
        Update job state.

        Args:
            job_id: Job identifier
            **updates: Fields to update
        """
        with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Job not found: {job_id}")
                return

            job = self._jobs[job_id]
            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            self._notify('job_updated', job)
            logger.debug(f"Job updated: {job_id}")

    def remove_job(self, job_id: str):
        """Remove job from state."""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs.pop(job_id)
                self._notify('job_removed', job)
                logger.debug(f"Job removed: {job_id}")

    def get_job(self, job_id: str) -> Optional[JobState]:
        """Get job state."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[JobState]:
        """Get all job states."""
        with self._lock:
            return list(self._jobs.values())

    def get_jobs_by_status(self, status: JobStatus) -> List[JobState]:
        """Get jobs with specific status."""
        with self._lock:
            return [j for j in self._jobs.values() if j.status == status]

    def get_active_jobs(self) -> List[JobState]:
        """Get all active (running/paused) jobs."""
        with self._lock:
            return [
                j for j in self._jobs.values()
                if j.status in (JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.PENDING)
            ]

    # Resource management

    def update_resources(self, resources: SystemResources):
        """Update system resource metrics."""
        with self._lock:
            self._resources = resources
            self._notify('resources_updated', resources)

    def get_resources(self) -> Optional[SystemResources]:
        """Get current resource metrics."""
        with self._lock:
            return self._resources

    # Error management

    def add_error(self, error_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Add error to error list."""
        with self._lock:
            error_entry = {
                'timestamp': datetime.utcnow(),
                'type': error_type,
                'message': message,
                'context': context or {}
            }
            self._errors.append(error_entry)

            # Keep last 100 errors
            if len(self._errors) > 100:
                self._errors.pop(0)

            self._notify('error_added', error_entry)
            logger.error(f"{error_type}: {message}")

    def get_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors."""
        with self._lock:
            return self._errors[-limit:]

    def clear_errors(self):
        """Clear all errors."""
        with self._lock:
            self._errors.clear()
            self._notify('errors_cleared', {})

    # Statistics

    def get_stats(self) -> Dict[str, Any]:
        """Get application statistics."""
        with self._lock:
            total_jobs = len(self._jobs)
            by_status = {}
            for status in JobStatus:
                by_status[status.value] = len(self.get_jobs_by_status(status))

            return {
                'total_jobs': total_jobs,
                'by_status': by_status,
                'active_jobs': len(self.get_active_jobs()),
                'error_count': len(self._errors),
                'resources': self._resources
            }

    def clear(self):
        """Clear all state (for testing)."""
        with self._lock:
            self._jobs.clear()
            self._errors.clear()
            self._resources = None
            logger.info("App state cleared")
