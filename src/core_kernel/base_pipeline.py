"""
Base Pipeline Module

Provides base implementation for pipelines.
Implements common pipeline functionality and execution flow.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .interfaces import IPipeline, IStep, StepResult, ExecutionStatus
from .exceptions import (
    PipelineCompilationError,
    PipelineExecutionError,
    CircularDependencyError,
    MissingDependencyError
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """Metrics for pipeline execution."""

    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    total_duration: float = 0.0
    step_durations: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "total_duration": self.total_duration,
            "success_rate": self.get_success_rate(),
            "step_durations": self.step_durations
        }

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100


class BasePipeline(IPipeline):
    """
    Base pipeline implementation.

    Features:
    - Step management
    - Dependency resolution
    - Execution orchestration
    - Error handling
    - Metrics collection
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base pipeline.

        Args:
            name: Pipeline name
            config: Optional pipeline configuration
        """
        self.name = name
        self.config = config or {}
        self.steps: Dict[str, IStep] = {}
        self.execution_order: List[str] = []
        self.compiled = False
        self.metrics = PipelineMetrics()
        logger.info(f"Initialized pipeline: {name}")

    def add_step(self, step: IStep) -> None:
        """
        Add a step to the pipeline.

        Args:
            step: Step to add
        """
        step_name = step.get_name() if hasattr(step, 'get_name') else str(step)
        self.steps[step_name] = step
        self.compiled = False  # Mark as needing recompilation
        logger.debug(f"Added step to pipeline {self.name}: {step_name}")

    def compile(self) -> bool:
        """
        Compile the pipeline.

        Returns:
            True if compilation succeeded
        """
        logger.info(f"Compiling pipeline: {self.name}")

        try:
            # Validate all steps
            for name, step in self.steps.items():
                if not step.validate():
                    raise PipelineCompilationError(
                        self.name,
                        f"Step validation failed: {name}"
                    )

            # Resolve dependencies and determine execution order
            self.execution_order = self._topological_sort()

            self.compiled = True
            logger.info(
                f"Pipeline compiled successfully: {self.name} "
                f"({len(self.execution_order)} steps)"
            )
            return True

        except Exception as e:
            logger.error(f"Pipeline compilation failed: {e}")
            self.compiled = False
            raise

    def execute(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, StepResult]:
        """
        Execute the pipeline.

        Args:
            context: Optional execution context

        Returns:
            Dictionary mapping step names to results
        """
        if not self.compiled:
            logger.info(f"Pipeline not compiled, compiling now: {self.name}")
            self.compile()

        context = context or {}
        context.setdefault('pipeline_name', self.name)

        logger.info(f"Executing pipeline: {self.name}")
        start_time = datetime.now()

        results: Dict[str, StepResult] = {}
        self.metrics = PipelineMetrics(total_steps=len(self.execution_order))

        try:
            # Execute steps in order
            for step_name in self.execution_order:
                step = self.steps[step_name]

                # Check if dependencies succeeded
                if not self._check_dependencies(step_name, results):
                    logger.warning(
                        f"Skipping step {step_name} due to failed dependencies"
                    )
                    results[step_name] = StepResult(
                        status=ExecutionStatus.SKIPPED,
                        data=None,
                        metadata={"reason": "dependency_failed"}
                    )
                    self.metrics.skipped_steps += 1
                    continue

                # Execute step
                result = self._execute_step(step, step_name, context)
                results[step_name] = result

                # Update metrics
                if result.is_success:
                    self.metrics.completed_steps += 1
                elif result.is_failure:
                    self.metrics.failed_steps += 1

                    # Check if should stop on error
                    if self.config.get('stop_on_error', True):
                        logger.error(
                            f"Stopping pipeline {self.name} due to step failure: {step_name}"
                        )
                        break

            # Calculate total duration
            end_time = datetime.now()
            self.metrics.total_duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Pipeline execution complete: {self.name} "
                f"({self.metrics.completed_steps}/{self.metrics.total_steps} successful)"
            )

            return results

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise PipelineExecutionError(
                self.name,
                cause=e
            )

    def _execute_step(
        self,
        step: IStep,
        step_name: str,
        context: Dict[str, Any]
    ) -> StepResult:
        """
        Execute a single step.

        Args:
            step: Step to execute
            step_name: Step name
            context: Execution context

        Returns:
            Step result
        """
        logger.debug(f"Executing step: {step_name}")
        step_start = datetime.now()

        try:
            # Add step name to context
            step_context = context.copy()
            step_context['step_name'] = step_name

            # Execute step
            result = step.execute(step_context)

            # Record duration
            duration = (datetime.now() - step_start).total_seconds()
            self.metrics.step_durations[step_name] = duration

            logger.info(
                f"Step completed: {step_name} ({result.status.value}) "
                f"in {duration:.3f}s"
            )

            return result

        except Exception as e:
            duration = (datetime.now() - step_start).total_seconds()
            self.metrics.step_durations[step_name] = duration

            logger.error(f"Step execution failed: {step_name} - {e}")

            return StepResult(
                status=ExecutionStatus.FAILED,
                data=None,
                error=e,
                metadata={"duration": duration}
            )

    def _check_dependencies(
        self,
        step_name: str,
        results: Dict[str, StepResult]
    ) -> bool:
        """
        Check if step dependencies succeeded.

        Args:
            step_name: Step name
            results: Results so far

        Returns:
            True if all dependencies succeeded
        """
        step = self.steps[step_name]
        dependencies = step.get_dependencies()

        for dep in dependencies:
            if dep not in results:
                # Dependency not executed yet
                return False

            if not results[dep].is_success:
                # Dependency failed
                return False

        return True

    def _topological_sort(self) -> List[str]:
        """
        Perform topological sort of steps based on dependencies.

        Returns:
            Ordered list of step names

        Raises:
            CircularDependencyError: If circular dependency detected
            MissingDependencyError: If dependency not found
        """
        # Build adjacency list
        graph: Dict[str, List[str]] = {}
        in_degree: Dict[str, int] = {}

        for step_name, step in self.steps.items():
            graph[step_name] = step.get_dependencies()
            in_degree[step_name] = 0

        # Calculate in-degrees
        for step_name in self.steps:
            for dep in graph[step_name]:
                if dep not in self.steps:
                    raise MissingDependencyError(step_name, dep)
                in_degree[dep] = in_degree.get(dep, 0) + 1

        # Find all nodes with no incoming edges
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Remove node from queue
            current = queue.pop(0)
            result.append(current)

            # For each neighbor, reduce in-degree
            for step_name, deps in graph.items():
                if current in deps:
                    in_degree[step_name] -= 1
                    if in_degree[step_name] == 0:
                        queue.append(step_name)

        # Check if all nodes processed (no cycle)
        if len(result) != len(self.steps):
            raise CircularDependencyError(
                cycle=list(self.steps.keys())
            )

        return result

    def get_execution_order(self) -> List[str]:
        """
        Get the execution order of steps.

        Returns:
            Ordered list of step names
        """
        if not self.compiled:
            self.compile()
        return self.execution_order.copy()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get pipeline metrics.

        Returns:
            Metrics dictionary
        """
        return self.metrics.to_dict()

    def reset(self) -> None:
        """Reset pipeline state."""
        self.metrics = PipelineMetrics()
        logger.debug(f"Reset pipeline: {self.name}")

    def validate(self) -> bool:
        """
        Validate pipeline configuration.

        Returns:
            True if valid
        """
        if not self.steps:
            logger.warning(f"Pipeline {self.name} has no steps")
            return False

        try:
            self.compile()
            return True
        except Exception as e:
            logger.error(f"Pipeline validation failed: {e}")
            return False
