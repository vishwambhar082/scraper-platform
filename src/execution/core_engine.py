"""
Core execution engine - single source of truth for all pipeline executions.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List
from enum import Enum
import threading
import logging
from datetime import datetime
from queue import Queue, Empty
import traceback

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """Execution lifecycle states"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    CRASHED = "crashed"


@dataclass
class ExecutionContext:
    """Single source of truth for execution state"""
    run_id: str
    state: ExecutionState
    pipeline_id: str
    source: str
    run_type: str
    environment: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    current_step: Optional[str] = None
    progress: float = 0.0
    total_steps: int = 0
    completed_steps: int = 0
    error: Optional[str] = None
    traceback: Optional[str] = None

    # Control signals
    pause_signal: threading.Event = field(default_factory=threading.Event)
    stop_signal: threading.Event = field(default_factory=threading.Event)
    resume_signal: threading.Event = field(default_factory=threading.Event)

    # Checkpointing
    completed_step_ids: set = field(default_factory=set)
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'run_id': self.run_id,
            'state': self.state.value,
            'pipeline_id': self.pipeline_id,
            'source': self.source,
            'run_type': self.run_type,
            'environment': self.environment,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'current_step': self.current_step,
            'progress': self.progress,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'error': self.error,
            'metadata': self.metadata,
        }


class CoreExecutionEngine:
    """
    Single authoritative execution engine for all pipeline executions.

    Responsibilities:
    - Owns all execution state
    - Propagates control signals (pause/stop/resume)
    - Manages checkpoints
    - Coordinates with UI via event callbacks
    - Ensures thread-safe operations
    """

    def __init__(self):
        self._executions: Dict[str, ExecutionContext] = {}
        self._lock = threading.RLock()
        self._event_callbacks: List[Callable[[str, dict], None]] = []
        self._executor_thread: Optional[threading.Thread] = None
        self._running = False
        self._command_queue: Queue = Queue()

    def start_execution(
        self,
        run_id: str,
        pipeline_id: str,
        source: str,
        run_type: str = "FULL_REFRESH",
        environment: str = "dev",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionContext:
        """
        Start new execution.

        Args:
            run_id: Unique run identifier
            pipeline_id: Pipeline to execute
            source: Data source name
            run_type: Type of run (FULL_REFRESH, DELTA, etc.)
            environment: Execution environment (dev, staging, prod)
            metadata: Additional metadata

        Returns:
            ExecutionContext for this execution

        Raises:
            ValueError: If run_id already exists
        """
        with self._lock:
            if run_id in self._executions:
                raise ValueError(f"Execution {run_id} already exists")

            ctx = ExecutionContext(
                run_id=run_id,
                state=ExecutionState.PENDING,
                pipeline_id=pipeline_id,
                source=source,
                run_type=run_type,
                environment=environment,
                started_at=datetime.utcnow(),
                metadata=metadata or {}
            )
            self._executions[run_id] = ctx

            # Queue execution command
            self._command_queue.put(('start', run_id))

            # Emit event
            self._emit_event('execution_started', {
                'run_id': run_id,
                'pipeline_id': pipeline_id,
                'source': source,
                'run_type': run_type,
                'environment': environment
            })

            # Ensure executor thread is running
            self._ensure_executor_running()

            logger.info(f"Execution started: {run_id} (pipeline: {pipeline_id})")
            return ctx

    def pause_execution(self, run_id: str) -> bool:
        """
        Pause running execution.

        Args:
            run_id: Run to pause

        Returns:
            True if paused, False if not running
        """
        with self._lock:
            ctx = self._executions.get(run_id)
            if not ctx or ctx.state != ExecutionState.RUNNING:
                logger.warning(f"Cannot pause execution {run_id}: state is {ctx.state if ctx else 'not found'}")
                return False

            ctx.pause_signal.set()
            ctx.state = ExecutionState.PAUSED
            self._emit_event('execution_paused', {'run_id': run_id})
            logger.info(f"Execution paused: {run_id}")
            return True

    def resume_execution(self, run_id: str) -> bool:
        """
        Resume paused execution.

        Args:
            run_id: Run to resume

        Returns:
            True if resumed, False if not paused
        """
        with self._lock:
            ctx = self._executions.get(run_id)
            if not ctx or ctx.state != ExecutionState.PAUSED:
                logger.warning(f"Cannot resume execution {run_id}: state is {ctx.state if ctx else 'not found'}")
                return False

            ctx.pause_signal.clear()
            ctx.resume_signal.set()
            ctx.state = ExecutionState.RUNNING
            self._emit_event('execution_resumed', {'run_id': run_id})
            logger.info(f"Execution resumed: {run_id}")
            return True

    def stop_execution(self, run_id: str, force: bool = False) -> bool:
        """
        Stop execution (graceful or forced).

        Args:
            run_id: Run to stop
            force: If True, force immediate stop

        Returns:
            True if stopped, False if not found
        """
        with self._lock:
            ctx = self._executions.get(run_id)
            if not ctx:
                logger.warning(f"Cannot stop execution {run_id}: not found")
                return False

            if force:
                ctx.state = ExecutionState.STOPPED
                ctx.finished_at = datetime.utcnow()
                self._emit_event('execution_force_stopped', {'run_id': run_id})
                logger.info(f"Execution force stopped: {run_id}")
            else:
                ctx.stop_signal.set()
                ctx.state = ExecutionState.STOPPING
                self._emit_event('execution_stopping', {'run_id': run_id})
                logger.info(f"Execution stopping: {run_id}")

            return True

    def update_progress(
        self,
        run_id: str,
        progress: float,
        current_step: Optional[str] = None,
        completed_steps: Optional[int] = None,
        total_steps: Optional[int] = None
    ):
        """
        Update execution progress.

        Args:
            run_id: Run to update
            progress: Progress percentage (0.0-1.0)
            current_step: Current step name
            completed_steps: Number of completed steps
            total_steps: Total number of steps
        """
        with self._lock:
            ctx = self._executions.get(run_id)
            if not ctx:
                return

            ctx.progress = progress
            if current_step:
                ctx.current_step = current_step
            if completed_steps is not None:
                ctx.completed_steps = completed_steps
            if total_steps is not None:
                ctx.total_steps = total_steps

            self._emit_event('execution_progress', {
                'run_id': run_id,
                'progress': progress,
                'current_step': current_step,
                'completed_steps': completed_steps,
                'total_steps': total_steps
            })

    def complete_execution(self, run_id: str, success: bool = True, error: Optional[str] = None):
        """
        Mark execution as completed.

        Args:
            run_id: Run to complete
            success: True if successful, False if failed
            error: Error message if failed
        """
        with self._lock:
            ctx = self._executions.get(run_id)
            if not ctx:
                return

            ctx.state = ExecutionState.COMPLETED if success else ExecutionState.FAILED
            ctx.finished_at = datetime.utcnow()
            ctx.progress = 1.0

            if error:
                ctx.error = error
                ctx.traceback = traceback.format_exc()

            event_type = 'execution_completed' if success else 'execution_failed'
            self._emit_event(event_type, {
                'run_id': run_id,
                'success': success,
                'error': error,
                'duration': (ctx.finished_at - ctx.started_at).total_seconds() if ctx.started_at else 0
            })

            logger.info(f"Execution {'completed' if success else 'failed'}: {run_id}")

    def get_execution_state(self, run_id: str) -> Optional[ExecutionContext]:
        """Get current execution state"""
        with self._lock:
            return self._executions.get(run_id)

    def list_active_executions(self) -> List[ExecutionContext]:
        """List all active executions"""
        with self._lock:
            return [
                ctx for ctx in self._executions.values()
                if ctx.state in (ExecutionState.RUNNING, ExecutionState.PAUSED, ExecutionState.STOPPING)
            ]

    def list_all_executions(self) -> List[ExecutionContext]:
        """List all executions"""
        with self._lock:
            return list(self._executions.values())

    def checkpoint(self, run_id: str, step_id: str, data: Dict[str, Any]):
        """
        Save checkpoint for execution step.

        Args:
            run_id: Run identifier
            step_id: Step identifier
            data: Checkpoint data
        """
        with self._lock:
            ctx = self._executions.get(run_id)
            if ctx:
                ctx.completed_step_ids.add(step_id)
                ctx.checkpoint_data[step_id] = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data
                }
                self._emit_event('checkpoint_saved', {
                    'run_id': run_id,
                    'step_id': step_id
                })
                logger.debug(f"Checkpoint saved: {run_id}/{step_id}")

    def can_resume_from_checkpoint(self, run_id: str) -> bool:
        """Check if execution can resume from checkpoint"""
        with self._lock:
            ctx = self._executions.get(run_id)
            return ctx is not None and len(ctx.completed_step_ids) > 0

    def get_checkpoint_data(self, run_id: str, step_id: str) -> Optional[Dict[str, Any]]:
        """Get checkpoint data for step"""
        with self._lock:
            ctx = self._executions.get(run_id)
            if ctx and step_id in ctx.checkpoint_data:
                return ctx.checkpoint_data[step_id]['data']
            return None

    def subscribe_events(self, callback: Callable[[str, dict], None]):
        """
        Subscribe to execution events.

        Args:
            callback: Function to call with (event_type, data)
        """
        self._event_callbacks.append(callback)
        logger.debug(f"Event subscriber added (total: {len(self._event_callbacks)})")

    def unsubscribe_events(self, callback: Callable[[str, dict], None]):
        """Unsubscribe from execution events"""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
            logger.debug(f"Event subscriber removed (total: {len(self._event_callbacks)})")

    def _emit_event(self, event_type: str, data: dict):
        """Emit event to all subscribers"""
        for callback in self._event_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Event callback error for {event_type}: {e}")

    def _ensure_executor_running(self):
        """Ensure executor thread is running"""
        if not self._running:
            self._running = True
            self._executor_thread = threading.Thread(
                target=self._executor_loop,
                daemon=True,
                name="CoreExecutionEngine"
            )
            self._executor_thread.start()
            logger.info("CoreExecutionEngine thread started")

    def _executor_loop(self):
        """Main execution monitoring loop"""
        logger.info("CoreExecutionEngine executor loop started")

        while self._running:
            try:
                # Process commands
                try:
                    command, run_id = self._command_queue.get(timeout=0.1)
                    self._process_command(command, run_id)
                except Empty:
                    pass

                # Monitor active executions for signals
                for ctx in self.list_active_executions():
                    # Check stop signal
                    if ctx.stop_signal.is_set() and ctx.state != ExecutionState.STOPPING:
                        self._handle_stop(ctx.run_id)

                    # Check pause signal
                    if ctx.pause_signal.is_set() and ctx.state == ExecutionState.RUNNING:
                        # Pause is already set in pause_execution()
                        pass

            except Exception as e:
                logger.error(f"Executor loop error: {e}", exc_info=True)

        logger.info("CoreExecutionEngine executor loop stopped")

    def _process_command(self, command: str, run_id: str):
        """Process execution command"""
        try:
            if command == 'start':
                ctx = self.get_execution_state(run_id)
                if ctx:
                    ctx.state = ExecutionState.RUNNING
                    self._emit_event('execution_running', {'run_id': run_id})
                    logger.debug(f"Execution command processed: {command} for {run_id}")
        except Exception as e:
            logger.error(f"Command processing error: {e}", exc_info=True)

    def _handle_stop(self, run_id: str):
        """Handle execution stop"""
        with self._lock:
            ctx = self._executions.get(run_id)
            if ctx:
                ctx.state = ExecutionState.STOPPED
                ctx.finished_at = datetime.utcnow()
                self._emit_event('execution_stopped', {
                    'run_id': run_id,
                    'duration': (ctx.finished_at - ctx.started_at).total_seconds() if ctx.started_at else 0
                })
                logger.info(f"Execution stopped: {run_id}")

    def shutdown(self):
        """Graceful shutdown of execution engine"""
        logger.info("Shutting down CoreExecutionEngine...")
        self._running = False

        # Stop all active executions
        active = self.list_active_executions()
        if active:
            logger.info(f"Stopping {len(active)} active executions...")
            for ctx in active:
                self.stop_execution(ctx.run_id, force=True)

        # Wait for executor thread
        if self._executor_thread and self._executor_thread.is_alive():
            self._executor_thread.join(timeout=5)

        logger.info("CoreExecutionEngine shutdown complete")

    def get_stats(self) -> Dict[str, Any]:
        """Get execution engine statistics"""
        with self._lock:
            total = len(self._executions)
            active = len(self.list_active_executions())
            by_state = {}
            for ctx in self._executions.values():
                by_state[ctx.state.value] = by_state.get(ctx.state.value, 0) + 1

            return {
                'total_executions': total,
                'active_executions': active,
                'by_state': by_state,
                'subscriber_count': len(self._event_callbacks),
                'is_running': self._running
            }
