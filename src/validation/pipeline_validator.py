"""
Pipeline Validator Module

Validates complete scraper pipelines for correctness and optimization.
Checks data flow, dependencies, and resource usage.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineIssueType(str, Enum):
    """Types of pipeline issues."""
    CIRCULAR_DEPENDENCY = "circular_dependency"
    MISSING_DEPENDENCY = "missing_dependency"
    DEAD_CODE = "dead_code"
    RESOURCE_LEAK = "resource_leak"
    INVALID_CONFIG = "invalid_config"
    PERFORMANCE = "performance"


@dataclass
class PipelineIssue:
    """Pipeline validation issue."""

    issue_type: PipelineIssueType
    severity: str  # "error", "warning", "info"
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion
        }


@dataclass
class PipelineValidationResult:
    """Result of pipeline validation."""

    pipeline_name: str
    is_valid: bool
    issues: List[PipelineIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> List[PipelineIssue]:
        """Get error-level issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[PipelineIssue]:
        """Get warning-level issues."""
        return [i for i in self.issues if i.severity == "warning"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [i.to_dict() for i in self.issues],
            "metrics": self.metrics
        }


class PipelineValidator:
    """
    Validates scraper pipeline configurations.

    Features:
    - Dependency graph validation
    - Resource usage analysis
    - Dead code detection
    - Performance optimization suggestions
    """

    def __init__(self):
        """Initialize pipeline validator."""
        logger.info("Initialized PipelineValidator")

    def validate(self, pipeline_config: Dict[str, Any]) -> PipelineValidationResult:
        """
        Validate a pipeline configuration.

        Args:
            pipeline_config: Pipeline configuration dictionary

        Returns:
            Validation result
        """
        pipeline_name = pipeline_config.get("name", "unnamed")
        logger.info(f"Validating pipeline: {pipeline_name}")

        issues: List[PipelineIssue] = []

        # Extract steps
        steps = pipeline_config.get("steps", [])

        if not steps:
            issues.append(PipelineIssue(
                issue_type=PipelineIssueType.INVALID_CONFIG,
                severity="error",
                message="Pipeline has no steps defined",
                suggestion="Add at least one step to the pipeline"
            ))
        else:
            # Validate step dependencies
            issues.extend(self._validate_dependencies(steps))

            # Check for dead code
            issues.extend(self._detect_dead_code(steps))

            # Validate resource usage
            issues.extend(self._validate_resources(steps))

            # Check for performance issues
            issues.extend(self._check_performance(steps, pipeline_config))

        # Calculate metrics
        metrics = self._calculate_metrics(steps, pipeline_config)

        # Determine validity
        has_errors = any(i.severity == "error" for i in issues)
        is_valid = not has_errors

        result = PipelineValidationResult(
            pipeline_name=pipeline_name,
            is_valid=is_valid,
            issues=issues,
            metrics=metrics
        )

        logger.info(
            f"Pipeline validation complete: {len(result.errors)} errors, "
            f"{len(result.warnings)} warnings"
        )

        return result

    def _validate_dependencies(self, steps: List[Dict[str, Any]]) -> List[PipelineIssue]:
        """Validate step dependencies."""
        issues = []

        # Build dependency graph
        step_names = {step.get("name", f"step_{i}") for i, step in enumerate(steps)}

        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")
            depends_on = step.get("depends_on", [])

            if isinstance(depends_on, str):
                depends_on = [depends_on]

            # Check for missing dependencies
            for dep in depends_on:
                if dep not in step_names:
                    issues.append(PipelineIssue(
                        issue_type=PipelineIssueType.MISSING_DEPENDENCY,
                        severity="error",
                        message=f"Step '{step_name}' depends on non-existent step '{dep}'",
                        location=f"steps[{i}]",
                        suggestion=f"Remove dependency or add step '{dep}'"
                    ))

        # Check for circular dependencies
        circular = self._detect_circular_dependencies(steps)
        if circular:
            issues.append(PipelineIssue(
                issue_type=PipelineIssueType.CIRCULAR_DEPENDENCY,
                severity="error",
                message=f"Circular dependency detected: {' -> '.join(circular)}",
                suggestion="Remove circular dependencies to allow execution"
            ))

        return issues

    def _detect_circular_dependencies(self, steps: List[Dict[str, Any]]) -> Optional[List[str]]:
        """Detect circular dependencies using DFS."""
        # Build adjacency list
        graph: Dict[str, List[str]] = {}
        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")
            depends_on = step.get("depends_on", [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            graph[step_name] = depends_on

        # DFS to detect cycles
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if dfs(node):
                    return path

        return None

    def _detect_dead_code(self, steps: List[Dict[str, Any]]) -> List[PipelineIssue]:
        """Detect unreachable or unused steps."""
        issues = []

        # Build reverse dependency graph
        used_by: Dict[str, Set[str]] = {}
        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")
            depends_on = step.get("depends_on", [])

            if isinstance(depends_on, str):
                depends_on = [depends_on]

            for dep in depends_on:
                if dep not in used_by:
                    used_by[dep] = set()
                used_by[dep].add(step_name)

        # Check each step
        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")

            # Check if step is used by anyone (except last steps)
            if step_name not in used_by and i < len(steps) - 1:
                # Check if it's an export or output step
                step_type = step.get("type", "")
                if step_type not in ["export", "output", "save"]:
                    issues.append(PipelineIssue(
                        issue_type=PipelineIssueType.DEAD_CODE,
                        severity="warning",
                        message=f"Step '{step_name}' output is not used by any other step",
                        location=f"steps[{i}]",
                        suggestion="Remove step or connect it to downstream steps"
                    ))

        return issues

    def _validate_resources(self, steps: List[Dict[str, Any]]) -> List[PipelineIssue]:
        """Validate resource usage."""
        issues = []

        browser_steps = 0
        concurrent_browsers = 0

        for i, step in enumerate(steps):
            step_type = step.get("type", "")

            # Check browser usage
            if step_type in ["fetch", "browser", "render"]:
                browser_steps += 1

                # Check if step runs in parallel
                if step.get("parallel", False):
                    parallel_count = step.get("max_workers", 1)
                    concurrent_browsers += parallel_count
                else:
                    concurrent_browsers = max(concurrent_browsers, 1)

        # Warn about high browser usage
        if concurrent_browsers > 5:
            issues.append(PipelineIssue(
                issue_type=PipelineIssueType.RESOURCE_LEAK,
                severity="warning",
                message=f"Pipeline may use up to {concurrent_browsers} concurrent browsers",
                suggestion="Consider reducing parallelism to conserve resources"
            ))

        return issues

    def _check_performance(
        self,
        steps: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[PipelineIssue]:
        """Check for performance issues."""
        issues = []

        # Check for sequential expensive operations
        expensive_types = {"fetch", "browser", "render", "llm", "ai"}
        sequential_expensive = []

        for step in steps:
            step_type = step.get("type", "")
            if step_type in expensive_types and not step.get("parallel", False):
                sequential_expensive.append(step_type)

        if len(sequential_expensive) > 3:
            issues.append(PipelineIssue(
                issue_type=PipelineIssueType.PERFORMANCE,
                severity="info",
                message=f"Pipeline has {len(sequential_expensive)} sequential expensive operations",
                suggestion="Consider enabling parallelization where possible"
            ))

        # Check timeout configuration
        global_timeout = config.get("timeout")
        if global_timeout and global_timeout < 30:
            issues.append(PipelineIssue(
                issue_type=PipelineIssueType.PERFORMANCE,
                severity="warning",
                message=f"Global timeout is very low: {global_timeout}s",
                suggestion="Increase timeout to reduce failure rate"
            ))

        return issues

    def _calculate_metrics(
        self,
        steps: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate pipeline metrics."""
        step_types: Dict[str, int] = {}

        for step in steps:
            step_type = step.get("type", "unknown")
            step_types[step_type] = step_types.get(step_type, 0) + 1

        return {
            "total_steps": len(steps),
            "step_types": step_types,
            "has_parallelization": any(s.get("parallel") for s in steps),
            "max_depth": self._calculate_max_depth(steps),
            "estimated_duration": self._estimate_duration(steps, config)
        }

    def _calculate_max_depth(self, steps: List[Dict[str, Any]]) -> int:
        """Calculate maximum dependency depth."""
        # Build dependency graph and calculate depth
        depths: Dict[str, int] = {}

        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")
            depends_on = step.get("depends_on", [])

            if isinstance(depends_on, str):
                depends_on = [depends_on]

            if not depends_on:
                depths[step_name] = 0
            else:
                max_dep_depth = max(
                    depths.get(dep, 0) for dep in depends_on
                )
                depths[step_name] = max_dep_depth + 1

        return max(depths.values()) if depths else 0

    def _estimate_duration(
        self,
        steps: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> float:
        """Estimate pipeline duration in seconds."""
        # Simple estimation based on step types
        type_durations = {
            "fetch": 5.0,
            "browser": 10.0,
            "parse": 1.0,
            "transform": 0.5,
            "validate": 0.5,
            "export": 2.0,
            "llm": 15.0,
            "ai": 15.0
        }

        total = 0.0
        for step in steps:
            step_type = step.get("type", "unknown")
            duration = type_durations.get(step_type, 3.0)
            total += duration

        return total


def validate_pipeline(pipeline_config: Dict[str, Any]) -> PipelineValidationResult:
    """
    Convenience function to validate a pipeline.

    Args:
        pipeline_config: Pipeline configuration

    Returns:
        Validation result
    """
    validator = PipelineValidator()
    return validator.validate(pipeline_config)
