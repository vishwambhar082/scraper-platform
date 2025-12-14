"""
Tests for CoreExecutionEngine.
"""

import pytest
import time
from datetime import datetime
from execution import CoreExecutionEngine, ExecutionState


class TestCoreExecutionEngine:
    """Test suite for CoreExecutionEngine"""

    @pytest.fixture
    def engine(self):
        """Create execution engine"""
        engine = CoreExecutionEngine()
        yield engine
        engine.shutdown()

    def test_start_execution(self, engine):
        """Test starting execution"""
        ctx = engine.start_execution(
            run_id="test-001",
            pipeline_id="test-pipeline",
            source="test-source",
            run_type="FULL_REFRESH",
            environment="dev"
        )

        assert ctx.run_id == "test-001"
        assert ctx.pipeline_id == "test-pipeline"
        assert ctx.state == ExecutionState.PENDING
        assert ctx.started_at is not None

    def test_duplicate_run_id(self, engine):
        """Test that duplicate run_id raises error"""
        engine.start_execution(
            run_id="test-001",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        with pytest.raises(ValueError, match="already exists"):
            engine.start_execution(
                run_id="test-001",
                pipeline_id="test-pipeline",
                source="test-source"
            )

    def test_pause_resume(self, engine):
        """Test pause and resume"""
        ctx = engine.start_execution(
            run_id="test-002",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Wait for execution to start
        time.sleep(0.2)

        # Pause
        assert engine.pause_execution("test-002") is True
        ctx = engine.get_execution_state("test-002")
        assert ctx.state == ExecutionState.PAUSED

        # Resume
        assert engine.resume_execution("test-002") is True
        ctx = engine.get_execution_state("test-002")
        assert ctx.state == ExecutionState.RUNNING

    def test_stop_execution(self, engine):
        """Test stopping execution"""
        ctx = engine.start_execution(
            run_id="test-003",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Stop gracefully
        assert engine.stop_execution("test-003") is True
        time.sleep(0.2)

        ctx = engine.get_execution_state("test-003")
        assert ctx.state in (ExecutionState.STOPPING, ExecutionState.STOPPED)

    def test_force_stop(self, engine):
        """Test force stopping execution"""
        ctx = engine.start_execution(
            run_id="test-004",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Force stop
        assert engine.stop_execution("test-004", force=True) is True

        ctx = engine.get_execution_state("test-004")
        assert ctx.state == ExecutionState.STOPPED
        assert ctx.finished_at is not None

    def test_progress_updates(self, engine):
        """Test progress updates"""
        ctx = engine.start_execution(
            run_id="test-005",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Update progress
        engine.update_progress(
            run_id="test-005",
            progress=0.5,
            current_step="step-2",
            completed_steps=2,
            total_steps=4
        )

        ctx = engine.get_execution_state("test-005")
        assert ctx.progress == 0.5
        assert ctx.current_step == "step-2"
        assert ctx.completed_steps == 2
        assert ctx.total_steps == 4

    def test_complete_execution(self, engine):
        """Test completing execution"""
        ctx = engine.start_execution(
            run_id="test-006",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Complete successfully
        engine.complete_execution("test-006", success=True)

        ctx = engine.get_execution_state("test-006")
        assert ctx.state == ExecutionState.COMPLETED
        assert ctx.progress == 1.0
        assert ctx.finished_at is not None

    def test_failed_execution(self, engine):
        """Test failed execution"""
        ctx = engine.start_execution(
            run_id="test-007",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Fail execution
        engine.complete_execution("test-007", success=False, error="Test error")

        ctx = engine.get_execution_state("test-007")
        assert ctx.state == ExecutionState.FAILED
        assert ctx.error == "Test error"
        assert ctx.finished_at is not None

    def test_checkpointing(self, engine):
        """Test checkpoint functionality"""
        ctx = engine.start_execution(
            run_id="test-008",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # Save checkpoints
        engine.checkpoint("test-008", "step-1", {"data": "value1"})
        engine.checkpoint("test-008", "step-2", {"data": "value2"})

        ctx = engine.get_execution_state("test-008")
        assert "step-1" in ctx.completed_step_ids
        assert "step-2" in ctx.completed_step_ids

        # Retrieve checkpoint data
        data1 = engine.get_checkpoint_data("test-008", "step-1")
        assert data1 == {"data": "value1"}

    def test_can_resume_from_checkpoint(self, engine):
        """Test checkpoint resume detection"""
        ctx = engine.start_execution(
            run_id="test-009",
            pipeline_id="test-pipeline",
            source="test-source"
        )

        # No checkpoints yet
        assert engine.can_resume_from_checkpoint("test-009") is False

        # Add checkpoint
        engine.checkpoint("test-009", "step-1", {"data": "value"})

        # Can resume now
        assert engine.can_resume_from_checkpoint("test-009") is True

    def test_list_active_executions(self, engine):
        """Test listing active executions"""
        # Start multiple executions
        engine.start_execution("test-010", "pipeline", "source")
        engine.start_execution("test-011", "pipeline", "source")
        engine.start_execution("test-012", "pipeline", "source")

        time.sleep(0.2)

        active = engine.list_active_executions()
        assert len(active) >= 3

        # Complete one
        engine.complete_execution("test-010")

        active = engine.list_active_executions()
        assert len(active) >= 2

    def test_event_subscription(self, engine):
        """Test event subscription"""
        events = []

        def callback(event_type, data):
            events.append((event_type, data))

        engine.subscribe_events(callback)

        # Start execution
        engine.start_execution("test-013", "pipeline", "source")

        time.sleep(0.1)

        # Should have received started event
        assert len(events) > 0
        assert events[0][0] == 'execution_started'
        assert events[0][1]['run_id'] == "test-013"

    def test_unsubscribe_events(self, engine):
        """Test event unsubscription"""
        events = []

        def callback(event_type, data):
            events.append((event_type, data))

        engine.subscribe_events(callback)
        engine.start_execution("test-014", "pipeline", "source")
        time.sleep(0.1)

        initial_count = len(events)

        # Unsubscribe
        engine.unsubscribe_events(callback)

        # Start another execution
        engine.start_execution("test-015", "pipeline", "source")
        time.sleep(0.1)

        # Should not receive new events
        assert len(events) == initial_count

    def test_get_stats(self, engine):
        """Test statistics retrieval"""
        engine.start_execution("test-016", "pipeline", "source")
        engine.start_execution("test-017", "pipeline", "source")

        stats = engine.get_stats()

        assert stats['total_executions'] >= 2
        assert stats['active_executions'] >= 2
        assert 'by_state' in stats
        assert stats['is_running'] is True

    def test_shutdown(self, engine):
        """Test graceful shutdown"""
        # Start executions
        engine.start_execution("test-018", "pipeline", "source")
        engine.start_execution("test-019", "pipeline", "source")

        time.sleep(0.2)

        # Shutdown
        engine.shutdown()

        # All executions should be stopped
        stats = engine.get_stats()
        assert stats['is_running'] is False
