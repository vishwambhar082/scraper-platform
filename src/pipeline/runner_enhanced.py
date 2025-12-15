"""
Enhanced Pipeline Runner with Checkpointing and Pause/Resume

Extends the base PipelineRunner with:
- Step-level checkpointing
- Pause/resume capabilities
- Breakpoint support
- Crash recovery
- Graceful shutdown

Author: Scraper Platform Team
Date: 2025-12-13
"""

from __future__ import annotations

import time
import uuid
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from src.common.logging_utils import get_logger
from .checkpoint import get_checkpoint_store
from .compiler import CompiledPipeline
from .step import PipelineStep, StepResult, StepType

log = get_logger("pipeline.runner_enhanced")


@dataclass
class RunContext:
    """Runtime context for pipeline execution."""

    run_id: str
    source: str
    environment: str = "prod"
    run_type: str = "FULL_REFRESH"
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    paused: bool = False
    stop_requested: bool = False
    breakpoints: Set[str] = field(default_factory=set)

    def get_step_output(self, step_id: str) -> Any:
        """Get output from a completed step."""
        result = self.step_results.get(step_id)
        return result.output if result else None

    def is_step_complete(self, step_id: str) -> bool:
        """Check if a step has completed."""
        return step_id in self.step_results

    def all_dependencies_met(self, step: PipelineStep) -> bool:
        """Check if all dependencies for a step are satisfied."""
        return all(self.is_step_complete(dep) for dep in step.depends_on)


@dataclass
class RunResult:
    """Result of a complete pipeline run."""

    run_id: str
    source: str
    status: str  # 'success', 'failed', 'partial', 'paused'
    duration_seconds: float
    step_results: Dict[str, StepResult]
    error: Optional[str] = None
    item_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == "success"

    @property
    def failed_steps(self) -> List[str]:
        return [
            step_id for step_id, result in self.step_results.items()
            if not result.success
        ]


class EnhancedPipelineRunner:
    """Enhanced pipeline runner with checkpointing and pause/resume.

    Features:
    - Step-level checkpointing for crash recovery
    - Pause/resume execution from any step
    - Breakpoint support for debugging
    - Graceful shutdown handling
    - Parallel execution with dependency resolution
    - Resume from checkpoint after crash
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        enable_checkpointing: bool = True,
        checkpoint_db_path: Optional[str] = None,
    ):
        """Initialize enhanced pipeline runner.

        Args:
            max_workers: Maximum parallel workers (default: 4)
            enable_checkpointing: Enable checkpoint system (default: True)
            checkpoint_db_path: Path to checkpoint database
        """
        self.max_workers = max_workers or 4
        self.enable_checkpointing = enable_checkpointing
        self.checkpoint_store = (
            get_checkpoint_store(checkpoint_db_path) if enable_checkpointing else None
        )
        self._active_runs: Dict[str, RunContext] = {}
        self._lock = threading.RLock()

    def run(
        self,
        pipeline: CompiledPipeline,
        source: str,
        environment: str = "prod",
        run_type: str = "FULL_REFRESH",
        params: Optional[Dict[str, Any]] = None,
        *,
        run_id: Optional[str] = None,
        recorder: Optional[Any] = None,
        progress_callback: Optional[Callable[[StepResult], None]] = None,
        resume_from_checkpoint: bool = False,
        breakpoints: Optional[Set[str]] = None,
    ) -> RunResult:
        """Execute a compiled pipeline with checkpointing support.

        Args:
            pipeline: Compiled pipeline to execute
            source: Source name (e.g., 'alfabeta')
            environment: Environment ('dev', 'staging', 'prod')
            run_type: Run type ('FULL_REFRESH', 'DELTA', etc.)
            params: Additional runtime parameters
            run_id: Optional run ID (generated if not provided)
            recorder: Optional run recorder
            progress_callback: Optional callback for step completion
            resume_from_checkpoint: Resume from existing checkpoint
            breakpoints: Optional set of step IDs to pause at

        Returns:
            RunResult with execution status and results
        """
        run_id = run_id or self._generate_run_id()
        start_time = time.time()

        # Create or restore context
        if resume_from_checkpoint and self.checkpoint_store:
            context = self._restore_context(run_id, source, environment, run_type, params, breakpoints)
            if not context:
                log.warning(f"No checkpoint found for {run_id}, starting fresh")
                context = self._create_context(
                    run_id, source, environment, run_type, params, breakpoints
                )
        else:
            context = self._create_context(
                run_id, source, environment, run_type, params, breakpoints
            )

        # Register active run
        with self._lock:
            self._active_runs[run_id] = context

        # Create checkpoint if enabled
        if self.enable_checkpointing and self.checkpoint_store:
            self.checkpoint_store.create_checkpoint(
                run_id=run_id,
                source=source,
                pipeline_name=pipeline.name,
                total_steps=len(pipeline.steps),
                environment=environment,
                run_type=run_type,
                params=params,
                metadata=context.metadata,
            )

        log.info(
            "Starting pipeline run",
            extra={
                "run_id": run_id,
                "pipeline": pipeline.name,
                "source": source,
                "environment": environment,
                "resume": resume_from_checkpoint,
            },
        )

        try:
            # Execute pipeline steps
            self._execute_pipeline(
                pipeline, context, recorder=recorder, progress_callback=progress_callback
            )

            # Determine final status
            status = self._determine_status(pipeline, context)

            # Collect failed steps
            failed_steps = {
                step_id: result.error or result.status
                for step_id, result in context.step_results.items()
                if not result.success
            }
            error = None
            if status != "success" and not error and failed_steps:
                error = "; ".join(f"{sid}: {msg}" for sid, msg in failed_steps.items())

            # Extract item count
            item_count = self._extract_item_count(context)

        except KeyboardInterrupt:
            log.info(f"Pipeline run {run_id} interrupted by user")
            status = "paused"
            error = "Interrupted by user"
            item_count = None

            if self.enable_checkpointing and self.checkpoint_store:
                self.checkpoint_store.update_checkpoint_status(run_id, "paused")

        except Exception as exc:
            log.error("Pipeline execution failed", exc_info=True, extra={"run_id": run_id})
            status = "failed"
            error = str(exc)
            item_count = None

            if self.enable_checkpointing and self.checkpoint_store:
                self.checkpoint_store.update_checkpoint_status(run_id, "failed")

        context.finished_at = datetime.utcnow()
        duration = time.time() - start_time

        # Update checkpoint on completion
        if self.enable_checkpointing and self.checkpoint_store and status in ("success", "failed"):
            self.checkpoint_store.update_checkpoint_status(run_id, status)

        # Unregister active run
        with self._lock:
            self._active_runs.pop(run_id, None)

        result = RunResult(
            run_id=run_id,
            source=source,
            status=status,
            duration_seconds=duration,
            step_results=context.step_results,
            error=error,
            item_count=item_count,
            metadata={
                **(context.metadata or {}),
                **({"failed_steps": failed_steps} if failed_steps else {}),
            },
        )

        log.info(
            "Pipeline run completed",
            extra={
                "run_id": run_id,
                "status": status,
                "duration": f"{duration:.2f}s",
                "steps_total": len(pipeline.steps),
                "steps_succeeded": len([r for r in context.step_results.values() if r.success]),
            },
        )

        return result

    def pause_run(self, run_id: str) -> bool:
        """Pause an active pipeline run.

        Args:
            run_id: Run identifier

        Returns:
            True if paused successfully
        """
        with self._lock:
            context = self._active_runs.get(run_id)
            if not context:
                log.warning(f"Cannot pause: run {run_id} not active")
                return False

            context.paused = True
            log.info(f"Paused pipeline run {run_id}")

            if self.enable_checkpointing and self.checkpoint_store:
                self.checkpoint_store.update_checkpoint_status(run_id, "paused")

            return True

    def resume_run(self, run_id: str) -> bool:
        """Resume a paused pipeline run.

        Args:
            run_id: Run identifier

        Returns:
            True if resumed successfully
        """
        with self._lock:
            context = self._active_runs.get(run_id)
            if not context:
                log.warning(f"Cannot resume: run {run_id} not active")
                return False

            context.paused = False
            log.info(f"Resumed pipeline run {run_id}")

            if self.enable_checkpointing and self.checkpoint_store:
                self.checkpoint_store.update_checkpoint_status(run_id, "active")

            return True

    def stop_run(self, run_id: str) -> bool:
        """Request graceful stop of pipeline run.

        Args:
            run_id: Run identifier

        Returns:
            True if stop requested successfully
        """
        with self._lock:
            context = self._active_runs.get(run_id)
            if not context:
                log.warning(f"Cannot stop: run {run_id} not active")
                return False

            context.stop_requested = True
            log.info(f"Stop requested for pipeline run {run_id}")
            return True

    def set_breakpoints(self, run_id: str, step_ids: Set[str]) -> bool:
        """Set breakpoints for a pipeline run.

        Args:
            run_id: Run identifier
            step_ids: Set of step IDs to break at

        Returns:
            True if breakpoints set successfully
        """
        with self._lock:
            context = self._active_runs.get(run_id)
            if not context:
                log.warning(f"Cannot set breakpoints: run {run_id} not active")
                return False

            context.breakpoints = step_ids
            log.info(f"Set {len(step_ids)} breakpoints for run {run_id}")
            return True

    def get_active_runs(self) -> List[str]:
        """Get list of active run IDs.

        Returns:
            List of active run IDs
        """
        with self._lock:
            return list(self._active_runs.keys())

    def get_run_context(self, run_id: str) -> Optional[RunContext]:
        """Get context for an active run.

        Args:
            run_id: Run identifier

        Returns:
            Run context or None if not found
        """
        with self._lock:
            return self._active_runs.get(run_id)

    def _create_context(
        self,
        run_id: str,
        source: str,
        environment: str,
        run_type: str,
        params: Optional[Dict[str, Any]],
        breakpoints: Optional[Set[str]],
    ) -> RunContext:
        """Create a new run context."""
        return RunContext(
            run_id=run_id,
            source=source,
            environment=environment,
            run_type=run_type,
            params=params or {},
            started_at=datetime.utcnow(),
            breakpoints=breakpoints or set(),
        )

    def _restore_context(
        self,
        run_id: str,
        source: str,
        environment: str,
        run_type: str,
        params: Optional[Dict[str, Any]],
        breakpoints: Optional[Set[str]],
    ) -> Optional[RunContext]:
        """Restore context from checkpoint.

        Args:
            run_id: Run identifier
            source: Source name
            environment: Environment
            run_type: Run type
            params: Runtime parameters
            breakpoints: Breakpoints

        Returns:
            Restored context or None if checkpoint not found
        """
        if not self.checkpoint_store:
            return None

        checkpoint = self.checkpoint_store.get_checkpoint(run_id)
        if not checkpoint or not self.checkpoint_store.can_resume(run_id):
            return None

        # Restore step results from checkpoint
        step_checkpoints = self.checkpoint_store.get_step_checkpoints(run_id)
        step_results = {}

        for step_cp in step_checkpoints:
            if step_cp.status == "completed":
                step_results[step_cp.step_id] = StepResult(
                    step_id=step_cp.step_id,
                    status="success",
                    duration_seconds=step_cp.duration_seconds or 0.0,
                    output=step_cp.output,
                )

        log.info(
            f"Restored {len(step_results)} completed steps from checkpoint {run_id}"
        )

        return RunContext(
            run_id=run_id,
            source=source,
            environment=environment,
            run_type=run_type,
            params=params or {},
            step_results=step_results,
            started_at=checkpoint.created_at,
            breakpoints=breakpoints or set(),
        )

    def _execute_pipeline(
        self,
        pipeline: CompiledPipeline,
        context: RunContext,
        *,
        recorder: Optional[Any] = None,
        progress_callback: Optional[Callable[[StepResult], None]] = None,
    ) -> None:
        """Execute all pipeline steps with dependency resolution."""
        # Build dependency graph
        step_map = {step.id: step for step in pipeline.steps}
        dependents = self._build_dependents_map(pipeline.steps)

        # Categorize steps
        export_steps = [s.id for s in pipeline.steps if s.type == StepType.EXPORT]
        export_order = {step_id: idx for idx, step_id in enumerate(export_steps)}

        # Track ready and pending steps (exclude already completed)
        completed = set(context.step_results.keys())
        ready: Set[str] = {
            s.id for s in pipeline.steps
            if not s.depends_on and s.id not in completed
        }
        pending: Set[str] = {s.id for s in pipeline.steps if s.id not in completed} - ready

        log.info(
            f"Pipeline execution: {len(completed)} completed, {len(ready)} ready, {len(pending)} pending"
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            while ready or futures or pending:
                # Check for pause/stop
                if context.stop_requested:
                    log.info("Stop requested, halting execution")
                    break

                if context.paused:
                    log.info("Execution paused, waiting...")
                    time.sleep(0.5)
                    continue

                # Submit ready steps
                for step_id in list(ready):
                    # Check breakpoint
                    if step_id in context.breakpoints:
                        log.info(f"Breakpoint hit at step {step_id}, pausing")
                        context.paused = True
                        context.breakpoints.remove(step_id)
                        break

                    step = step_map[step_id]

                    # Export steps run sequentially
                    if step.type == StepType.EXPORT:
                        completed_exports = [
                            s for s in export_steps if s in context.step_results
                        ]
                        if export_order[step_id] != len(completed_exports):
                            continue  # Wait for earlier exports

                        ready.remove(step_id)
                        result = self._execute_step(
                            step, context, recorder=recorder, progress_callback=progress_callback
                        )
                        context.step_results[step_id] = result
                        self._save_step_checkpoint(run_id=context.run_id, step_id=step_id, result=result)
                        self._mark_dependents_ready(
                            step_id, dependents, step_map, context, ready, pending
                        )
                    else:
                        # Parallel execution
                        ready.remove(step_id)
                        future = executor.submit(
                            self._execute_step, step, context, recorder, progress_callback
                        )
                        futures[future] = step_id

                # Wait for futures to complete
                if futures:
                    done_futures = []
                    for future in list(futures.keys()):
                        if future.done():
                            done_futures.append(future)

                    for future in done_futures:
                        step_id = futures.pop(future)
                        result = future.result()
                        context.step_results[step_id] = result
                        self._save_step_checkpoint(run_id=context.run_id, step_id=step_id, result=result)
                        self._mark_dependents_ready(
                            step_id, dependents, step_map, context, ready, pending
                        )

                    if not done_futures and futures:
                        time.sleep(0.1)  # Avoid busy waiting

                # Check for deadlock
                if not ready and not futures and pending:
                    unmet = [
                        (sid, [d for d in step_map[sid].depends_on if d not in context.step_results])
                        for sid in pending
                    ]
                    raise RuntimeError(f"Pipeline deadlock detected. Unmet dependencies: {unmet}")

    def _execute_step(
        self,
        step: PipelineStep,
        context: RunContext,
        recorder: Optional[Any] = None,
        progress_callback: Optional[Callable[[StepResult], None]] = None,
    ) -> StepResult:
        """Execute a single step with retries."""
        log.info("Executing step: %s (%s)", step.id, step.type.value)

        # Build runtime context with dependency outputs
        runtime_ctx = {
            "run_id": context.run_id,
            "source": context.source,
            "environment": context.environment,
            "run_type": context.run_type,
            **context.params,
        }

        # Add outputs from dependencies
        for dep_id in step.depends_on:
            runtime_ctx[dep_id] = context.get_step_output(dep_id)

        # Execute with retries
        for attempt in range(step.retry_count + 1):
            started_at = datetime.utcnow()
            result = step.execute(runtime_ctx)

            if result.success or attempt == step.retry_count:
                if not result.success and not step.required:
                    log.warning("Optional step %s failed but continuing", step.id)
                    result.status = "skipped"

                if recorder:
                    try:
                        recorder.record_step(
                            run_id=context.run_id,
                            name=step.id,
                            status=result.status,
                            started_at=started_at,
                            duration_seconds=int(result.duration_seconds),
                        )
                    except Exception:
                        log.debug("Failed to record step %s", step.id, exc_info=True)

                if progress_callback:
                    try:
                        progress_callback(result)
                    except Exception:
                        log.debug("Progress callback failed for %s", step.id, exc_info=True)

                return result

            log.warning("Step %s failed (attempt %d/%d)", step.id, attempt + 1, step.retry_count + 1)
            time.sleep(1.0 * (attempt + 1))

        return result

    def _save_step_checkpoint(self, run_id: str, step_id: str, result: StepResult) -> None:
        """Save step checkpoint."""
        if not self.enable_checkpointing or not self.checkpoint_store:
            return

        try:
            self.checkpoint_store.save_step(
                run_id=run_id,
                step_id=step_id,
                status="completed" if result.success else "failed",
                duration_seconds=result.duration_seconds,
                output=result.output,
                error=result.error,
            )
        except Exception as e:
            log.warning(f"Failed to save checkpoint for {step_id}: {e}")

    def _build_dependents_map(self, steps: List[PipelineStep]) -> Dict[str, List[str]]:
        """Build reverse dependency map."""
        dependents: Dict[str, List[str]] = defaultdict(list)
        for step in steps:
            for dep in step.depends_on:
                dependents[dep].append(step.id)
        return dict(dependents)

    def _mark_dependents_ready(
        self,
        completed_step_id: str,
        dependents: Dict[str, List[str]],
        step_map: Dict[str, PipelineStep],
        context: RunContext,
        ready: Set[str],
        pending: Set[str],
    ) -> None:
        """Mark dependent steps as ready if all dependencies are met."""
        for dependent_id in dependents.get(completed_step_id, []):
            if dependent_id in pending:
                step = step_map[dependent_id]
                if context.all_dependencies_met(step):
                    pending.remove(dependent_id)
                    ready.add(dependent_id)

    def _determine_status(self, pipeline: CompiledPipeline, context: RunContext) -> str:
        """Determine final pipeline status."""
        if context.paused or context.stop_requested:
            return "paused"

        total = len(pipeline.steps)
        completed = len(context.step_results)

        if completed < total:
            return "partial"

        failed = [r for r in context.step_results.values() if not r.success]
        if failed:
            all_optional = all(
                not next((s for s in pipeline.steps if s.id == step_id), PipelineStep(id="", type=StepType.CUSTOM, callable=lambda: None)).required
                for step_id in [r.step_id for r in failed]
            )
            return "success" if all_optional else "failed"

        return "success"

    def _extract_item_count(self, context: RunContext) -> Optional[int]:
        """Extract item count from step results."""
        for result in reversed(list(context.step_results.values())):
            if isinstance(result.output, (list, tuple)):
                return len(result.output)
            if isinstance(result.output, dict):
                if "item_count" in result.output:
                    return result.output["item_count"]
                if "records" in result.output and isinstance(result.output["records"], list):
                    return len(result.output["records"])
        return None

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique = uuid.uuid4().hex[:6].upper()
        return f"RUN-{timestamp}-{unique}"
