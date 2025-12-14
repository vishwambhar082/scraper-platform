"""
Centralized application state store with Redux-like pattern.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime
from enum import Enum
import copy
import threading
import logging

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobState:
    """State for a single job."""
    job_id: str
    source: str
    status: JobStatus
    run_type: str
    environment: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress: float = 0.0
    current_step: Optional[str] = None
    total_steps: int = 0
    completed_steps: int = 0
    error: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UIState:
    """UI component state."""
    selected_job_id: Optional[str] = None
    active_tab: str = "dashboard"
    log_filter_level: str = "INFO"
    log_search_text: str = ""
    auto_scroll: bool = True
    theme: str = "dark"
    notifications_enabled: bool = True


@dataclass
class SystemState:
    """System resource state."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    active_processes: int = 0
    last_updated: Optional[datetime] = None


@dataclass
class AppState:
    """
    Complete application state.

    This is the single source of truth for all application data.
    """
    # Job management
    jobs: Dict[str, JobState] = field(default_factory=dict)
    job_history: List[str] = field(default_factory=list)

    # UI state
    ui: UIState = field(default_factory=UIState)

    # System state
    system: SystemState = field(default_factory=SystemState)

    # Event history
    event_history: List[Dict[str, Any]] = field(default_factory=list)

    # Application metadata
    version: str = "1.0.0"
    initialized_at: datetime = field(default_factory=datetime.utcnow)
    last_modified: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        data = asdict(self)
        # Convert enums
        for job_id, job in data['jobs'].items():
            if 'status' in job:
                job['status'] = job['status'].value if hasattr(job['status'], 'value') else job['status']
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppState':
        """Create state from dictionary."""
        # Convert status strings back to enums
        if 'jobs' in data:
            for job_data in data['jobs'].values():
                if 'status' in job_data and isinstance(job_data['status'], str):
                    job_data['status'] = JobStatus(job_data['status'])
        return cls(**data)


class AppStore:
    """
    Centralized state store with Redux-like architecture.

    Features:
    - Single source of truth
    - Immutable state updates
    - Action-based mutations
    - Subscription system
    - Thread-safe operations
    """

    def __init__(self, initial_state: Optional[AppState] = None):
        """
        Initialize store.

        Args:
            initial_state: Optional initial state
        """
        self._state = initial_state or AppState()
        self._lock = threading.RLock()
        self._subscribers: Set[Callable[[AppState], None]] = set()
        self._middleware: List[Callable] = []
        self._history: List[AppState] = []
        self._max_history = 50
        self._action_count = 0

    def get_state(self) -> AppState:
        """Get current state (immutable copy)."""
        with self._lock:
            return copy.deepcopy(self._state)

    def dispatch(self, action: Any) -> AppState:
        """
        Dispatch an action to update state.

        Args:
            action: Action object with type and payload

        Returns:
            Updated state
        """
        with self._lock:
            # Save to history
            if len(self._history) >= self._max_history:
                self._history.pop(0)
            self._history.append(copy.deepcopy(self._state))

            # Apply middleware
            for middleware in self._middleware:
                action = middleware(self, action, self._state)
                if action is None:
                    return self._state

            # Apply reducer
            new_state = self._reduce(self._state, action)

            # Update modification time
            new_state.last_modified = datetime.utcnow()

            # Update state
            self._state = new_state
            self._action_count += 1

            # Notify subscribers
            self._notify_subscribers()

            return copy.deepcopy(self._state)

    def _reduce(self, state: AppState, action: Any) -> AppState:
        """
        Reduce state based on action (pure function).

        Args:
            state: Current state
            action: Action to apply

        Returns:
            New state
        """
        # Create a mutable copy
        new_state = copy.deepcopy(state)

        action_type = getattr(action, 'type', None)
        payload = getattr(action, 'payload', {})

        # Job actions
        if action_type == 'JOB_STARTED':
            job_id = payload['job_id']
            new_state.jobs[job_id] = JobState(
                job_id=job_id,
                source=payload.get('source', ''),
                status=JobStatus.RUNNING,
                run_type=payload.get('run_type', ''),
                environment=payload.get('environment', ''),
                started_at=datetime.utcnow()
            )
            if job_id not in new_state.job_history:
                new_state.job_history.append(job_id)

        elif action_type == 'JOB_PROGRESS':
            job_id = payload['job_id']
            if job_id in new_state.jobs:
                new_state.jobs[job_id].progress = payload.get('progress', 0.0)
                new_state.jobs[job_id].current_step = payload.get('current_step')
                new_state.jobs[job_id].completed_steps = payload.get('completed_steps', 0)
                new_state.jobs[job_id].total_steps = payload.get('total_steps', 0)

        elif action_type == 'JOB_COMPLETED':
            job_id = payload['job_id']
            if job_id in new_state.jobs:
                new_state.jobs[job_id].status = JobStatus.COMPLETED
                new_state.jobs[job_id].finished_at = datetime.utcnow()
                new_state.jobs[job_id].progress = 1.0

        elif action_type == 'JOB_FAILED':
            job_id = payload['job_id']
            if job_id in new_state.jobs:
                new_state.jobs[job_id].status = JobStatus.FAILED
                new_state.jobs[job_id].finished_at = datetime.utcnow()
                new_state.jobs[job_id].error = payload.get('error')

        elif action_type == 'JOB_PAUSED':
            job_id = payload['job_id']
            if job_id in new_state.jobs:
                new_state.jobs[job_id].status = JobStatus.PAUSED

        elif action_type == 'JOB_RESUMED':
            job_id = payload['job_id']
            if job_id in new_state.jobs:
                new_state.jobs[job_id].status = JobStatus.RUNNING

        elif action_type == 'JOB_CANCELLED':
            job_id = payload['job_id']
            if job_id in new_state.jobs:
                new_state.jobs[job_id].status = JobStatus.CANCELLED
                new_state.jobs[job_id].finished_at = datetime.utcnow()

        elif action_type == 'JOB_LOG':
            job_id = payload['job_id']
            if job_id in new_state.jobs:
                new_state.jobs[job_id].logs.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': payload.get('level', 'INFO'),
                    'message': payload.get('message', '')
                })
                # Limit log history
                if len(new_state.jobs[job_id].logs) > 1000:
                    new_state.jobs[job_id].logs = new_state.jobs[job_id].logs[-1000:]

        elif action_type == 'JOB_REMOVED':
            job_id = payload['job_id']
            if job_id in new_state.jobs:
                del new_state.jobs[job_id]

        # UI actions
        elif action_type == 'UI_SELECT_JOB':
            new_state.ui.selected_job_id = payload.get('job_id')

        elif action_type == 'UI_CHANGE_TAB':
            new_state.ui.active_tab = payload.get('tab', 'dashboard')

        elif action_type == 'UI_SET_LOG_FILTER':
            new_state.ui.log_filter_level = payload.get('level', 'INFO')

        elif action_type == 'UI_SET_LOG_SEARCH':
            new_state.ui.log_search_text = payload.get('text', '')

        elif action_type == 'UI_TOGGLE_AUTO_SCROLL':
            new_state.ui.auto_scroll = payload.get('enabled', True)

        elif action_type == 'UI_SET_THEME':
            new_state.ui.theme = payload.get('theme', 'dark')

        # System actions
        elif action_type == 'SYSTEM_UPDATE':
            new_state.system.cpu_percent = payload.get('cpu_percent', 0.0)
            new_state.system.memory_percent = payload.get('memory_percent', 0.0)
            new_state.system.disk_percent = payload.get('disk_percent', 0.0)
            new_state.system.network_bytes_sent = payload.get('network_bytes_sent', 0)
            new_state.system.network_bytes_recv = payload.get('network_bytes_recv', 0)
            new_state.system.active_processes = payload.get('active_processes', 0)
            new_state.system.last_updated = datetime.utcnow()

        # Event history
        elif action_type == 'EVENT_LOGGED':
            new_state.event_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'type': payload.get('event_type'),
                'data': payload.get('data', {})
            })
            # Limit history
            if len(new_state.event_history) > 10000:
                new_state.event_history = new_state.event_history[-10000:]

        return new_state

    def subscribe(self, callback: Callable[[AppState], None]) -> Callable[[], None]:
        """
        Subscribe to state changes.

        Args:
            callback: Function to call on state change

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._subscribers.add(callback)

        def unsubscribe():
            with self._lock:
                self._subscribers.discard(callback)

        return unsubscribe

    def _notify_subscribers(self) -> None:
        """Notify all subscribers of state change."""
        state_copy = copy.deepcopy(self._state)
        for callback in list(self._subscribers):
            try:
                callback(state_copy)
            except Exception as e:
                logger.error(f"Subscriber callback error: {e}")

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware function."""
        with self._lock:
            self._middleware.append(middleware)

    def get_history(self, count: int = 10) -> List[AppState]:
        """Get state history."""
        with self._lock:
            return list(self._history[-count:])

    def time_travel(self, index: int) -> None:
        """
        Travel to a previous state (debugging feature).

        Args:
            index: History index (negative for recent)
        """
        with self._lock:
            if -len(self._history) <= index < len(self._history):
                self._state = copy.deepcopy(self._history[index])
                self._notify_subscribers()
            else:
                logger.warning(f"Invalid history index: {index}")

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        with self._lock:
            return {
                'action_count': self._action_count,
                'subscriber_count': len(self._subscribers),
                'middleware_count': len(self._middleware),
                'history_size': len(self._history),
                'job_count': len(self._state.jobs),
                'event_count': len(self._state.event_history),
            }
