"""
Integration module for connecting execution engine and scheduler to UI.
"""

import logging
from pathlib import Path
from typing import Optional

from execution import CoreExecutionEngine, CheckpointManager, ResourceMonitor
from scheduler import DesktopScheduler, ScheduleConfig
from ui.state import AppStore, Action, ActionType

logger = logging.getLogger(__name__)


class ExecutionIntegration:
    """
    Integrates execution engine with UI state and event bus.

    This replaces polling-based updates with event-driven architecture.
    """

    def __init__(self, store: AppStore, event_bus):
        """
        Initialize execution integration.

        Args:
            store: AppStore for state management
            event_bus: EventBus for UI updates
        """
        self.store = store
        self.event_bus = event_bus

        # Initialize execution engine
        self.execution_engine = CoreExecutionEngine()

        # Initialize checkpoint manager
        checkpoint_db = Path.home() / '.scraper-platform' / 'checkpoints.db'
        self.checkpoint_manager = CheckpointManager(checkpoint_db)

        # Initialize resource monitor
        self.resource_monitor = ResourceMonitor(
            sample_interval=1.0,
            cpu_limit_percent=90.0,
            memory_limit_mb=4096
        )

        # Initialize scheduler
        scheduler_db = Path.home() / '.scraper-platform' / 'scheduler.db'
        self.scheduler = DesktopScheduler(scheduler_db, self.execution_engine)

        # Wire up event callbacks
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Setup event handlers for execution engine"""

        def on_execution_event(event_type: str, data: dict):
            """Handle execution events"""
            try:
                run_id = data.get('run_id')

                if event_type == 'execution_started':
                    # Update app state
                    self.store.dispatch(Action(
                        type=ActionType.JOB_STARTED,
                        payload={
                            'job_id': run_id,
                            'source': data.get('source', ''),
                            'run_type': data.get('run_type', ''),
                            'environment': data.get('environment', '')
                        }
                    ))

                    # Emit UI event
                    self.event_bus.emit_job_state_changed(run_id, 'running')

                elif event_type == 'execution_paused':
                    self.store.dispatch(Action(
                        type=ActionType.JOB_PAUSED,
                        payload={'job_id': run_id}
                    ))
                    self.event_bus.emit_job_state_changed(run_id, 'paused')

                elif event_type == 'execution_resumed':
                    self.store.dispatch(Action(
                        type=ActionType.JOB_RESUMED,
                        payload={'job_id': run_id}
                    ))
                    self.event_bus.emit_job_state_changed(run_id, 'running')

                elif event_type == 'execution_progress':
                    self.store.dispatch(Action(
                        type=ActionType.JOB_PROGRESS,
                        payload={
                            'job_id': run_id,
                            'progress': data.get('progress', 0.0),
                            'current_step': data.get('current_step'),
                            'completed_steps': data.get('completed_steps', 0),
                            'total_steps': data.get('total_steps', 0)
                        }
                    ))
                    self.event_bus.emit_progress(
                        run_id,
                        data.get('progress', 0.0),
                        data.get('current_step', '')
                    )

                elif event_type == 'execution_completed':
                    self.store.dispatch(Action(
                        type=ActionType.JOB_COMPLETED,
                        payload={'job_id': run_id}
                    ))
                    self.event_bus.emit_job_state_changed(run_id, 'completed')

                elif event_type == 'execution_failed':
                    self.store.dispatch(Action(
                        type=ActionType.JOB_FAILED,
                        payload={
                            'job_id': run_id,
                            'error': data.get('error')
                        }
                    ))
                    self.event_bus.emit_error(run_id, data.get('error', 'Unknown error'))

                elif event_type == 'execution_stopped':
                    self.store.dispatch(Action(
                        type=ActionType.JOB_CANCELLED,
                        payload={'job_id': run_id}
                    ))
                    self.event_bus.emit_job_state_changed(run_id, 'stopped')

                elif event_type == 'checkpoint_saved':
                    # Save to checkpoint manager
                    ctx = self.execution_engine.get_execution_state(run_id)
                    if ctx:
                        self.checkpoint_manager.save_execution_state(
                            run_id=run_id,
                            pipeline_id=ctx.pipeline_id,
                            source=ctx.source,
                            run_type=ctx.run_type,
                            environment=ctx.environment,
                            state=ctx.state.value,
                            started_at=ctx.started_at,
                            finished_at=ctx.finished_at,
                            progress=ctx.progress,
                            current_step=ctx.current_step,
                            total_steps=ctx.total_steps,
                            completed_steps=ctx.completed_steps,
                            error=ctx.error,
                            metadata=ctx.metadata
                        )

            except Exception as e:
                logger.error(f"Error handling execution event {event_type}: {e}", exc_info=True)

        # Subscribe to execution events
        self.execution_engine.subscribe_events(on_execution_event)

        # Subscribe to resource limit events
        def on_resource_limit(resource_type: str, value: float):
            """Handle resource limit exceeded"""
            logger.warning(f"Resource limit exceeded: {resource_type} = {value}")
            # Could pause executions, send alerts, etc.

        self.resource_monitor.subscribe_limit_exceeded(on_resource_limit)

    def start(self):
        """Start all components"""
        self.resource_monitor.start()
        self.scheduler.start()
        logger.info("ExecutionIntegration started")

    def shutdown(self):
        """Shutdown all components gracefully"""
        logger.info("Shutting down ExecutionIntegration...")

        # Stop scheduler
        self.scheduler.stop()

        # Stop resource monitor
        self.resource_monitor.stop()

        # Shutdown execution engine
        self.execution_engine.shutdown()

        logger.info("ExecutionIntegration shutdown complete")

    def start_job(
        self,
        source: str,
        run_type: str = "FULL_REFRESH",
        environment: str = "dev",
        pipeline_id: Optional[str] = None
    ) -> str:
        """
        Start a new job execution.

        Args:
            source: Data source name
            run_type: Type of run
            environment: Execution environment
            pipeline_id: Override pipeline ID

        Returns:
            Run ID
        """
        from datetime import datetime

        run_id = f"{source}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        pipeline = pipeline_id or source

        self.execution_engine.start_execution(
            run_id=run_id,
            pipeline_id=pipeline,
            source=source,
            run_type=run_type,
            environment=environment
        )

        return run_id

    def pause_job(self, run_id: str) -> bool:
        """Pause running job"""
        return self.execution_engine.pause_execution(run_id)

    def resume_job(self, run_id: str) -> bool:
        """Resume paused job"""
        return self.execution_engine.resume_execution(run_id)

    def stop_job(self, run_id: str, force: bool = False) -> bool:
        """Stop job"""
        return self.execution_engine.stop_execution(run_id, force=force)

    def get_active_jobs(self):
        """Get all active jobs"""
        return self.execution_engine.list_active_executions()

    def get_job_status(self, run_id: str):
        """Get job status"""
        return self.execution_engine.get_execution_state(run_id)

    def schedule_job(
        self,
        job_id: str,
        source: str,
        schedule_type: str,
        schedule_config: dict,
        pipeline_id: Optional[str] = None
    ) -> bool:
        """
        Schedule a job for automatic execution.

        Args:
            job_id: Unique job identifier
            source: Data source name
            schedule_type: 'once', 'interval', 'cron', 'manual'
            schedule_config: Schedule configuration
            pipeline_id: Override pipeline ID

        Returns:
            True if scheduled successfully
        """
        return self.scheduler.schedule_job(
            job_id=job_id,
            pipeline_id=pipeline_id or source,
            source=source,
            schedule_type=schedule_type,
            schedule_config=schedule_config
        )

    def get_stats(self) -> dict:
        """Get comprehensive statistics"""
        return {
            'execution_engine': self.execution_engine.get_stats(),
            'scheduler': self.scheduler.get_stats(),
            'resources': self.resource_monitor.get_stats()
        }
