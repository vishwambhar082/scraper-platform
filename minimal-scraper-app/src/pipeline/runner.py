"""Unified pipeline runner that executes compiled pipelines."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from src.common.logging_utils import get_logger
from .compiler import CompiledPipeline
from .step import PipelineStep, StepResult, StepType

log = get_logger("pipeline.runner")


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
    status: str  # 'success', 'failed', 'partial'
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


class PipelineRunner:
    """Executes compiled pipelines with dependency management and parallelization.
    
    This replaces:
    - core_kernel.execution_engine.ExecutionEngine
    - agents.orchestrator.AgentOrchestrator
    - pipeline_pack.agents.registry.run_pipeline
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or 4
        
    def run(
        self,
        pipeline: CompiledPipeline,
        source: str,
        environment: str = "prod",
        run_type: str = "FULL_REFRESH",
        params: Optional[Dict[str, Any]] = None,
    ) -> RunResult:
        """Execute a compiled pipeline.
        
        Args:
            pipeline: Compiled pipeline to execute
            source: Source name (e.g., 'alfabeta')
            environment: Environment ('dev', 'staging', 'prod')
            run_type: Run type ('FULL_REFRESH', 'DELTA', etc.)
            params: Additional runtime parameters
            
        Returns:
            RunResult with execution status and results
        """
        run_id = self._generate_run_id()
        start_time = time.time()
        
        context = RunContext(
            run_id=run_id,
            source=source,
            environment=environment,
            run_type=run_type,
            params=params or {},
            started_at=datetime.utcnow(),
        )
        
        log.info(
            "Starting pipeline run",
            extra={
                "run_id": run_id,
                "pipeline": pipeline.name,
                "source": source,
                "environment": environment,
            },
        )
        
        try:
            # Execute pipeline steps
            self._execute_pipeline(pipeline, context)
            
            # Determine final status
            status = self._determine_status(pipeline, context)
            error = None
            
            # Extract item count from last step if available
            item_count = self._extract_item_count(context)
            
        except Exception as exc:
            log.error("Pipeline execution failed", exc_info=True, extra={"run_id": run_id})
            status = "failed"
            error = str(exc)
            item_count = None
            
        context.finished_at = datetime.utcnow()
        duration = time.time() - start_time
        
        result = RunResult(
            run_id=run_id,
            source=source,
            status=status,
            duration_seconds=duration,
            step_results=context.step_results,
            error=error,
            item_count=item_count,
            metadata=context.metadata,
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
        
    def _execute_pipeline(self, pipeline: CompiledPipeline, context: RunContext) -> None:
        """Execute all pipeline steps with dependency resolution."""
        # Build dependency graph
        step_map = {step.id: step for step in pipeline.steps}
        dependents = self._build_dependents_map(pipeline.steps)
        
        # Categorize steps by type (export steps must run sequentially)
        export_steps = [s.id for s in pipeline.steps if s.type == StepType.EXPORT]
        export_order = {step_id: idx for idx, step_id in enumerate(export_steps)}
        
        # Track ready and pending steps
        ready: Set[str] = {s.id for s in pipeline.steps if not s.depends_on}
        pending: Set[str] = {s.id for s in pipeline.steps} - ready
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            while ready or futures or pending:
                # Submit ready steps (except export steps which run serially)
                for step_id in list(ready):
                    step = step_map[step_id]
                    
                    # Export steps run sequentially
                    if step.type == StepType.EXPORT:
                        # Only run if it's the next export in order
                        completed_exports = [
                            s for s in export_steps
                            if s in context.step_results
                        ]
                        if export_order[step_id] != len(completed_exports):
                            continue  # Wait for earlier exports
                            
                        # Run synchronously
                        ready.remove(step_id)
                        result = self._execute_step(step, context)
                        context.step_results[step_id] = result
                        self._mark_dependents_ready(step_id, dependents, step_map, context, ready, pending)
                    else:
                        # Parallel execution for non-export steps
                        ready.remove(step_id)
                        future = executor.submit(self._execute_step, step, context)
                        futures[future] = step_id
                
                # Wait for any future to complete
                if futures:
                    done, _ = as_completed(futures.keys(), timeout=1).__next__, None
                    if done:
                        for future in list(futures.keys()):
                            if future.done():
                                step_id = futures.pop(future)
                                result = future.result()
                                context.step_results[step_id] = result
                                self._mark_dependents_ready(
                                    step_id, dependents, step_map, context, ready, pending
                                )
                                
                # Check for deadlock
                if not ready and not futures and pending:
                    unmet = [
                        (sid, [d for d in step_map[sid].depends_on if d not in context.step_results])
                        for sid in pending
                    ]
                    raise RuntimeError(f"Pipeline deadlock detected. Unmet dependencies: {unmet}")
                    
    def _execute_step(self, step: PipelineStep, context: RunContext) -> StepResult:
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
            result = step.execute(runtime_ctx)
            
            if result.success or attempt == step.retry_count:
                if not result.success and not step.required:
                    log.warning("Optional step %s failed but continuing", step.id)
                    result.status = "skipped"
                return result
                
            log.warning("Step %s failed (attempt %d/%d)", step.id, attempt + 1, step.retry_count + 1)
            time.sleep(1.0 * (attempt + 1))  # Exponential backoff
            
        return result
        
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
        total = len(pipeline.steps)
        completed = len(context.step_results)
        
        if completed < total:
            return "partial"
            
        failed = [r for r in context.step_results.values() if not r.success]
        if failed:
            # Check if all failed steps were optional
            all_optional = all(
                not next((s for s in pipeline.steps if s.id == r.step_id), None).required
                for r in failed
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
