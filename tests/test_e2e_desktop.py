"""
End-to-end integration tests for desktop application.

Tests complete flow from job submission to completion.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import time

from src.execution.core_engine import CoreExecutionEngine, ExecutionState
from src.scheduler.local_scheduler import LocalScheduler, JobPriority, QueuedJob
from src.run_tracking.checkpoints import CheckpointManager
from src.core.cancellation import CancellationToken, CancellationError
from src.core.resource_governor import ResourceGovernor, ResourceLimits
from src.ui.app_state import AppState, JobStatus, JobState


class TestEndToEndExecution:
    """End-to-end execution tests."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            yield {
                'db': base / 'db',
                'output': base / 'output',
                'logs': base / 'logs'
            }

    @pytest.fixture
    def execution_engine(self):
        """Create execution engine."""
        return CoreExecutionEngine()

    @pytest.fixture
    def checkpoint_manager(self, temp_dirs):
        """Create checkpoint manager."""
        db_path = temp_dirs['db'] / 'checkpoints.db'
        mgr = CheckpointManager(db_path)
        yield mgr
        mgr.close()

    @pytest.fixture
    def app_state(self):
        """Create app state."""
        return AppState()

    def test_simple_execution_flow(self, execution_engine, checkpoint_manager):
        """Test simple execution from start to completion."""
        # Start execution
        run_id = "test-run-001"
        ctx = execution_engine.start_execution(
            run_id=run_id,
            pipeline_id="test-pipeline",
            source="test-source",
            run_type="manual",
            environment={"test": True}
        )

        assert ctx.run_id == run_id
        assert ctx.state == ExecutionState.RUNNING

        # Initialize checkpoint
        checkpoint_manager.init_job(
            job_id=run_id,
            pipeline_id="test-pipeline",
            source="test-source",
            total_steps=3
        )

        # Simulate step execution with checkpoints
        for i in range(3):
            step_id = f"step-{i}"

            # Save checkpoint
            checkpoint_manager.save_checkpoint(
                job_id=run_id,
                step_id=step_id,
                step_index=i,
                data={"result": f"data-{i}"},
                status='completed'
            )

            # Update progress
            progress = (i + 1) / 3.0
            execution_engine.update_progress(
                run_id=run_id,
                progress=progress,
                current_step=step_id,
                completed_steps=i + 1,
                total_steps=3
            )

        # Mark completed
        execution_engine.complete_execution(run_id, success=True)
        checkpoint_manager.mark_job_completed(run_id)

        # Verify final state
        final_ctx = execution_engine.get_execution_state(run_id)
        assert final_ctx.state == ExecutionState.COMPLETED
        assert final_ctx.progress == 1.0

        # Verify checkpoints
        checkpoints = checkpoint_manager.get_job_checkpoints(run_id)
        assert len(checkpoints) == 3

    def test_execution_with_cancellation(self, execution_engine):
        """Test execution with cancellation."""
        run_id = "test-run-002"

        # Start execution
        ctx = execution_engine.start_execution(
            run_id=run_id,
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Pause execution
        assert execution_engine.pause_execution(run_id)

        # Verify paused
        ctx = execution_engine.get_execution_state(run_id)
        assert ctx.state == ExecutionState.PAUSED

        # Resume
        assert execution_engine.resume_execution(run_id)
        ctx = execution_engine.get_execution_state(run_id)
        assert ctx.state == ExecutionState.RUNNING

        # Stop execution
        assert execution_engine.stop_execution(run_id)
        ctx = execution_engine.get_execution_state(run_id)
        assert ctx.state == ExecutionState.STOPPED

    def test_crash_recovery(self, checkpoint_manager):
        """Test crash recovery scenario."""
        # Simulate interrupted execution
        job_id = "crash-test-001"

        # Init job
        checkpoint_manager.init_job(
            job_id=job_id,
            pipeline_id="test-pipeline",
            source="test-source",
            total_steps=5
        )

        # Complete 3 steps
        for i in range(3):
            checkpoint_manager.save_checkpoint(
                job_id=job_id,
                step_id=f"step-{i}",
                step_index=i,
                data={"result": i},
                status='completed'
            )

        # Simulate crash (job still in 'running' state)

        # Recovery: list resumable jobs
        resumable = checkpoint_manager.list_resumable_jobs()
        assert len(resumable) == 1
        assert resumable[0]['job_id'] == job_id
        assert resumable[0]['completed_steps'] == 3
        assert resumable[0]['total_steps'] == 5

        # Get completed steps to resume from
        completed_steps = checkpoint_manager.get_completed_steps(job_id)
        assert len(completed_steps) == 3
        assert completed_steps == ['step-0', 'step-1', 'step-2']

    def test_scheduler_integration(self, temp_dirs, execution_engine):
        """Test scheduler with execution engine."""
        executed_jobs = []

        def executor(job: QueuedJob):
            """Test executor."""
            # Start execution
            ctx = execution_engine.start_execution(
                run_id=job.job_id,
                pipeline_id=job.pipeline_id,
                source=job.source
            )

            # Simulate work
            time.sleep(0.1)

            # Mark completed
            execution_engine.complete_execution(job.job_id, success=True)
            executed_jobs.append(job.job_id)

        # Create scheduler
        scheduler_db = temp_dirs['db'] / 'scheduler.db'
        scheduler = LocalScheduler(
            db_path=scheduler_db,
            executor=executor,
            max_concurrent=2
        )

        # Start scheduler
        scheduler.start()

        try:
            # Queue jobs
            for i in range(3):
                scheduler.queue_job(
                    job_id=f"job-{i}",
                    pipeline_id="test-pipeline",
                    source="test-source",
                    config={"index": i},
                    priority=JobPriority.NORMAL
                )

            # Wait for completion
            timeout = 5.0
            start = time.time()
            while len(executed_jobs) < 3 and (time.time() - start) < timeout:
                time.sleep(0.1)

            # Verify all executed
            assert len(executed_jobs) == 3

        finally:
            scheduler.stop()

    def test_resource_limits(self):
        """Test resource governor limits."""
        limits = ResourceLimits(
            max_cpu_percent=80.0,
            max_memory_percent=70.0,
            max_browsers=2
        )

        governor = ResourceGovernor(limits)

        # Check resources
        snapshot = governor.check_resources()
        assert snapshot.cpu_percent >= 0
        assert snapshot.memory_percent >= 0

        # Test browser limits
        if governor.can_start_browser():
            # Register browser
            governor.register_browser("browser-1")
            assert governor.browser_tracker.get_count() == 1

            # Register second
            if governor.can_start_browser():
                governor.register_browser("browser-2")
                assert governor.browser_tracker.get_count() == 2

                # Should hit limit
                assert not governor.can_start_browser()

            # Unregister
            governor.unregister_browser("browser-1")
            assert governor.browser_tracker.get_count() == 1

    def test_ui_state_integration(self, app_state):
        """Test UI state with execution updates."""
        events_received = []

        def subscriber(event_type: str, data):
            """Test subscriber."""
            events_received.append((event_type, data))

        app_state.subscribe(subscriber)

        # Add job
        job_state = JobState(
            job_id="ui-test-001",
            pipeline_id="test-pipeline",
            source="test-source",
            status=JobStatus.PENDING
        )
        app_state.add_job(job_state)

        # Update job
        app_state.update_job("ui-test-001", status=JobStatus.RUNNING, progress=0.5)

        # Add error
        app_state.add_error("test_error", "Test error message", {"job_id": "ui-test-001"})

        # Verify events
        assert len(events_received) >= 3
        assert events_received[0][0] == 'job_added'
        assert events_received[1][0] == 'job_updated'
        assert events_received[2][0] == 'error_added'

        # Verify state
        job = app_state.get_job("ui-test-001")
        assert job.status == JobStatus.RUNNING
        assert job.progress == 0.5

        errors = app_state.get_errors()
        assert len(errors) == 1


class TestCancellationFlow:
    """Test cancellation token propagation."""

    def test_cancellation_token_basic(self):
        """Test basic cancellation token."""
        token = CancellationToken()

        assert not token.is_cancelled()
        assert not token.is_paused()

        # Cancel
        token.cancel()
        assert token.is_cancelled()

        # Check should raise
        with pytest.raises(CancellationError):
            token.check()

    def test_pause_resume(self):
        """Test pause/resume."""
        token = CancellationToken()

        # Pause
        token.pause()
        assert token.is_paused()

        # Resume
        token.resume()
        assert not token.is_paused()

    def test_wait_while_paused(self):
        """Test blocking while paused."""
        token = CancellationToken()

        # Pause
        token.pause()

        # Should timeout waiting
        import threading

        def resume_after_delay():
            time.sleep(0.2)
            token.resume()

        thread = threading.Thread(target=resume_after_delay)
        thread.start()

        # Should block then continue
        start = time.time()
        token.wait_while_paused(check_interval=0.05)
        elapsed = time.time() - start

        assert elapsed >= 0.2
        thread.join()


class TestBootstrapFlow:
    """Test application bootstrap."""

    def test_bootstrap_first_run(self):
        """Test first-time bootstrap."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)

            from src.entrypoints.bootstrap import ApplicationBootstrap

            bootstrap = ApplicationBootstrap(app_dir, version="1.0.0")

            # Bootstrap
            assert bootstrap.bootstrap()

            # Verify config created
            config_file = app_dir / "config" / "app.json"
            assert config_file.exists()

            # Verify directories
            assert (app_dir / "logs").exists()
            assert (app_dir / "db").exists()
            assert (app_dir / "output").exists()

            # Shutdown
            bootstrap.shutdown()

            # Verify crash lock removed
            assert not bootstrap.crash_file.exists()

    def test_crash_detection(self):
        """Test crash detection and recovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)

            from src.entrypoints.bootstrap import ApplicationBootstrap

            # First run - create crash lock
            bootstrap1 = ApplicationBootstrap(app_dir, version="1.0.0")
            assert bootstrap1.bootstrap()

            # Don't call shutdown - simulate crash
            assert bootstrap1.crash_file.exists()

            # Second run - should detect crash
            bootstrap2 = ApplicationBootstrap(app_dir, version="1.0.0")

            # Should detect and recover from crash
            assert bootstrap2._check_crash()
            assert bootstrap2.bootstrap()

            # Cleanup
            bootstrap2.shutdown()


def test_complete_workflow():
    """Test complete workflow from job submission to completion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Setup components
        execution_engine = CoreExecutionEngine()
        checkpoint_mgr = CheckpointManager(base / 'checkpoints.db')
        app_state = AppState()

        # Track events
        state_events = []
        app_state.subscribe(lambda event, data: state_events.append(event))

        # Submit job
        run_id = "workflow-001"

        # Add to UI state
        app_state.add_job(JobState(
            job_id=run_id,
            pipeline_id="test-pipeline",
            source="test-source",
            status=JobStatus.PENDING
        ))

        # Start execution
        ctx = execution_engine.start_execution(
            run_id=run_id,
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Update UI state
        app_state.update_job(run_id, status=JobStatus.RUNNING)

        # Initialize checkpoints
        checkpoint_mgr.init_job(
            job_id=run_id,
            pipeline_id="test-pipeline",
            source="test-source",
            total_steps=3
        )

        # Execute steps
        for i in range(3):
            step_id = f"step-{i}"

            # Checkpoint
            checkpoint_mgr.save_checkpoint(
                job_id=run_id,
                step_id=step_id,
                step_index=i,
                data={"result": i}
            )

            # Update progress
            progress = (i + 1) / 3.0
            execution_engine.update_progress(
                run_id=run_id,
                progress=progress,
                current_step=step_id,
                completed_steps=i + 1,
                total_steps=3
            )

            app_state.update_job(run_id, progress=progress, current_step=step_id)

        # Complete
        execution_engine.complete_execution(run_id, success=True)
        checkpoint_mgr.mark_job_completed(run_id)
        checkpoint_mgr.close()  # Close DB connection
        app_state.update_job(run_id, status=JobStatus.COMPLETED)

        # Verify
        assert len(state_events) > 0
        final_job = app_state.get_job(run_id)
        assert final_job.status == JobStatus.COMPLETED
        assert final_job.progress == 1.0

        final_ctx = execution_engine.get_execution_state(run_id)
        assert final_ctx.state == ExecutionState.COMPLETED
