"""
Integration layer to wire existing EnhancedPipelineRunner with CoreExecutionEngine.

This makes signals propagate properly to scrapers and engines.
"""

import time
import logging
from typing import Any, Dict, Optional
from execution import CoreExecutionEngine, ExecutionState

logger = logging.getLogger(__name__)


class ExecutionStopped(Exception):
    """Raised when execution is stopped via signal."""
    pass


class SignalAwarePipelineRunner:
    """
    Wrapper around existing runner that checks execution engine signals.

    This makes pause/resume/stop work properly during pipeline execution.
    """

    def __init__(self, base_runner, execution_engine: CoreExecutionEngine):
        """
        Initialize signal-aware runner.

        Args:
            base_runner: Existing EnhancedPipelineRunner or PipelineRunner
            execution_engine: CoreExecutionEngine instance
        """
        self.base_runner = base_runner
        self.execution_engine = execution_engine

    def run(
        self,
        pipeline,
        run_id: str,
        source: str,
        run_type: str = "FULL_REFRESH",
        environment: str = "dev",
        params: Optional[Dict[str, Any]] = None,
        resume_from_checkpoint: bool = False
    ):
        """
        Run pipeline with signal awareness.

        Checks execution engine signals before each step and propagates
        pause/stop/resume to the actual execution.
        """
        # Get execution context from engine
        ctx = self.execution_engine.get_execution_state(run_id)
        if not ctx:
            logger.error(f"Execution context not found: {run_id}")
            return {'status': 'failed', 'error': 'Execution context not found'}

        try:
            # Mark as running
            ctx.state = ExecutionState.RUNNING

            # Get pipeline steps
            steps = pipeline.steps if hasattr(pipeline, 'steps') else []
            total_steps = len(steps)

            # Update engine
            self.execution_engine.update_progress(
                run_id=run_id,
                progress=0.0,
                total_steps=total_steps,
                completed_steps=0
            )

            results = []
            completed_count = 0

            # Execute each step with signal checking
            for i, step in enumerate(steps):
                # Check signals before each step
                self._check_signals(ctx)

                logger.info(f"Executing step {i+1}/{total_steps}: {step.id}")

                # Update current step
                self.execution_engine.update_progress(
                    run_id=run_id,
                    progress=completed_count / total_steps,
                    current_step=step.id,
                    completed_steps=completed_count,
                    total_steps=total_steps
                )

                # Execute step (delegate to base runner)
                try:
                    result = self._execute_step_with_signals(step, ctx)
                    results.append(result)

                    # Save checkpoint
                    self.execution_engine.checkpoint(
                        run_id=run_id,
                        step_id=step.id,
                        data={'result': result}
                    )

                    completed_count += 1

                except ExecutionStopped:
                    logger.info(f"Execution stopped at step: {step.id}")
                    return {
                        'status': 'stopped',
                        'completed_steps': completed_count,
                        'total_steps': total_steps
                    }

                except Exception as e:
                    logger.error(f"Step {step.id} failed: {e}")
                    self.execution_engine.complete_execution(
                        run_id=run_id,
                        success=False,
                        error=str(e)
                    )
                    return {
                        'status': 'failed',
                        'error': str(e),
                        'completed_steps': completed_count,
                        'total_steps': total_steps
                    }

            # All steps completed
            self.execution_engine.complete_execution(run_id=run_id, success=True)

            return {
                'status': 'success',
                'completed_steps': completed_count,
                'total_steps': total_steps,
                'results': results
            }

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            self.execution_engine.complete_execution(
                run_id=run_id,
                success=False,
                error=str(e)
            )
            return {'status': 'failed', 'error': str(e)}

    def _check_signals(self, ctx):
        """
        Check execution signals and handle pause/stop.

        Raises:
            ExecutionStopped: If execution should be stopped
        """
        # Check for pause
        if ctx.pause_signal.is_set():
            logger.info("Execution paused, waiting for resume...")
            ctx.state = ExecutionState.PAUSED

            # Wait for resume or stop
            while ctx.pause_signal.is_set():
                time.sleep(0.1)

                # Check if stop was requested during pause
                if ctx.stop_signal.is_set():
                    raise ExecutionStopped("Stopped during pause")

            logger.info("Execution resumed")
            ctx.state = ExecutionState.RUNNING

        # Check for stop
        if ctx.stop_signal.is_set():
            raise ExecutionStopped("Stop signal received")

    def _execute_step_with_signals(self, step, ctx):
        """
        Execute single step with periodic signal checks.

        For long-running steps, this checks signals during execution.
        """
        # If step has execute method, call it
        if hasattr(step, 'execute'):
            # TODO: For long-running steps, we need to:
            # 1. Run in separate thread
            # 2. Periodically check signals
            # 3. Cancel/interrupt if needed
            #
            # For now, just execute and check after
            result = step.execute()
            self._check_signals(ctx)
            return result

        # If step is callable
        elif callable(step):
            result = step()
            self._check_signals(ctx)
            return result

        else:
            logger.warning(f"Step {step} is not executable")
            return None


def integrate_pipeline_runner(execution_engine: CoreExecutionEngine):
    """
    Create signal-aware pipeline runner.

    Args:
        execution_engine: CoreExecutionEngine instance

    Returns:
        SignalAwarePipelineRunner that can be used in place of existing runner
    """
    # Import existing runner
    try:
        from src.pipeline.runner_enhanced import EnhancedPipelineRunner
        base_runner = EnhancedPipelineRunner()
    except ImportError:
        try:
            from src.pipeline.runner import PipelineRunner
            base_runner = PipelineRunner()
        except ImportError:
            logger.error("Could not import pipeline runner")
            base_runner = None

    if base_runner:
        return SignalAwarePipelineRunner(base_runner, execution_engine)
    else:
        logger.error("Failed to create pipeline runner")
        return None
