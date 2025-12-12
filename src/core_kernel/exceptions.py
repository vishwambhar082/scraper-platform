"""
Core Kernel Exceptions Module

Defines exception hierarchy for the core kernel.
Extends the base error framework with kernel-specific errors.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Base Kernel Exceptions
# ============================================================================

class KernelError(Exception):
    """Base exception for core kernel errors."""

    def __init__(self, message: str, **context):
        """
        Initialize kernel error.

        Args:
            message: Error message
            **context: Additional context
        """
        super().__init__(message)
        self.message = message
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "context": self.context
        }


# ============================================================================
# Pipeline Exceptions
# ============================================================================

class PipelineError(KernelError):
    """Base class for pipeline-related errors."""
    pass


class PipelineCompilationError(PipelineError):
    """Pipeline failed to compile."""

    def __init__(self, pipeline_name: str, reason: str, **context):
        """
        Initialize compilation error.

        Args:
            pipeline_name: Pipeline name
            reason: Compilation failure reason
            **context: Additional context
        """
        message = f"Pipeline '{pipeline_name}' compilation failed: {reason}"
        super().__init__(message, pipeline_name=pipeline_name, reason=reason, **context)
        self.pipeline_name = pipeline_name
        self.reason = reason


class PipelineExecutionError(PipelineError):
    """Pipeline execution failed."""

    def __init__(self, pipeline_name: str, step_name: Optional[str] = None, **context):
        """
        Initialize execution error.

        Args:
            pipeline_name: Pipeline name
            step_name: Optional step name where error occurred
            **context: Additional context
        """
        message = f"Pipeline '{pipeline_name}' execution failed"
        if step_name:
            message += f" at step '{step_name}'"
        super().__init__(message, pipeline_name=pipeline_name, step_name=step_name, **context)
        self.pipeline_name = pipeline_name
        self.step_name = step_name


class PipelineNotFoundError(PipelineError):
    """Pipeline not found in registry."""

    def __init__(self, pipeline_name: str):
        """
        Initialize not found error.

        Args:
            pipeline_name: Pipeline name
        """
        message = f"Pipeline not found: {pipeline_name}"
        super().__init__(message, pipeline_name=pipeline_name)
        self.pipeline_name = pipeline_name


# ============================================================================
# Step Exceptions
# ============================================================================

class StepError(KernelError):
    """Base class for step-related errors."""
    pass


class StepValidationError(StepError):
    """Step validation failed."""

    def __init__(self, step_name: str, reason: str, **context):
        """
        Initialize validation error.

        Args:
            step_name: Step name
            reason: Validation failure reason
            **context: Additional context
        """
        message = f"Step '{step_name}' validation failed: {reason}"
        super().__init__(message, step_name=step_name, reason=reason, **context)
        self.step_name = step_name
        self.reason = reason


class StepExecutionError(StepError):
    """Step execution failed."""

    def __init__(self, step_name: str, cause: Optional[Exception] = None, **context):
        """
        Initialize execution error.

        Args:
            step_name: Step name
            cause: Original exception that caused the error
            **context: Additional context
        """
        message = f"Step '{step_name}' execution failed"
        if cause:
            message += f": {str(cause)}"
        super().__init__(message, step_name=step_name, cause=str(cause) if cause else None, **context)
        self.step_name = step_name
        self.cause = cause


class StepTimeoutError(StepError):
    """Step execution timed out."""

    def __init__(self, step_name: str, timeout: float, **context):
        """
        Initialize timeout error.

        Args:
            step_name: Step name
            timeout: Timeout value in seconds
            **context: Additional context
        """
        message = f"Step '{step_name}' timed out after {timeout}s"
        super().__init__(message, step_name=step_name, timeout=timeout, **context)
        self.step_name = step_name
        self.timeout = timeout


# ============================================================================
# Dependency Exceptions
# ============================================================================

class DependencyError(KernelError):
    """Base class for dependency-related errors."""
    pass


class CircularDependencyError(DependencyError):
    """Circular dependency detected in pipeline."""

    def __init__(self, cycle: list, **context):
        """
        Initialize circular dependency error.

        Args:
            cycle: List of steps forming the cycle
            **context: Additional context
        """
        cycle_str = " -> ".join(cycle)
        message = f"Circular dependency detected: {cycle_str}"
        super().__init__(message, cycle=cycle, **context)
        self.cycle = cycle


class MissingDependencyError(DependencyError):
    """Required dependency not found."""

    def __init__(self, step_name: str, dependency: str, **context):
        """
        Initialize missing dependency error.

        Args:
            step_name: Step name
            dependency: Missing dependency name
            **context: Additional context
        """
        message = f"Step '{step_name}' depends on missing step '{dependency}'"
        super().__init__(message, step_name=step_name, dependency=dependency, **context)
        self.step_name = step_name
        self.dependency = dependency


# ============================================================================
# Processor Exceptions
# ============================================================================

class ProcessorError(KernelError):
    """Base class for processor-related errors."""
    pass


class ProcessorNotFoundError(ProcessorError):
    """Processor not found in registry."""

    def __init__(self, processor_name: str, **context):
        """
        Initialize not found error.

        Args:
            processor_name: Processor name
            **context: Additional context
        """
        message = f"Processor not found: {processor_name}"
        super().__init__(message, processor_name=processor_name, **context)
        self.processor_name = processor_name


class ProcessorInputError(ProcessorError):
    """Invalid input provided to processor."""

    def __init__(self, processor_name: str, reason: str, **context):
        """
        Initialize input error.

        Args:
            processor_name: Processor name
            reason: Reason for invalid input
            **context: Additional context
        """
        message = f"Invalid input for processor '{processor_name}': {reason}"
        super().__init__(message, processor_name=processor_name, reason=reason, **context)
        self.processor_name = processor_name
        self.reason = reason


class ProcessorConfigError(ProcessorError):
    """Invalid processor configuration."""

    def __init__(self, processor_name: str, config_error: str, **context):
        """
        Initialize config error.

        Args:
            processor_name: Processor name
            config_error: Configuration error description
            **context: Additional context
        """
        message = f"Invalid configuration for processor '{processor_name}': {config_error}"
        super().__init__(message, processor_name=processor_name, config_error=config_error, **context)
        self.processor_name = processor_name
        self.config_error = config_error


# ============================================================================
# Execution Exceptions
# ============================================================================

class ExecutionError(KernelError):
    """Base class for execution-related errors."""
    pass


class ExecutionNotFoundError(ExecutionError):
    """Execution record not found."""

    def __init__(self, execution_id: str, **context):
        """
        Initialize not found error.

        Args:
            execution_id: Execution ID
            **context: Additional context
        """
        message = f"Execution not found: {execution_id}"
        super().__init__(message, execution_id=execution_id, **context)
        self.execution_id = execution_id


class ExecutionCancelledError(ExecutionError):
    """Execution was cancelled."""

    def __init__(self, execution_id: str, reason: Optional[str] = None, **context):
        """
        Initialize cancelled error.

        Args:
            execution_id: Execution ID
            reason: Optional cancellation reason
            **context: Additional context
        """
        message = f"Execution cancelled: {execution_id}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, execution_id=execution_id, reason=reason, **context)
        self.execution_id = execution_id
        self.reason = reason


# ============================================================================
# Context Exceptions
# ============================================================================

class ContextError(KernelError):
    """Base class for context-related errors."""
    pass


class MissingContextError(ContextError):
    """Required context value missing."""

    def __init__(self, key: str, **context):
        """
        Initialize missing context error.

        Args:
            key: Missing context key
            **context: Additional context
        """
        message = f"Required context key missing: {key}"
        super().__init__(message, key=key, **context)
        self.key = key


class InvalidContextError(ContextError):
    """Invalid context value."""

    def __init__(self, key: str, expected_type: type, actual_type: type, **context):
        """
        Initialize invalid context error.

        Args:
            key: Context key
            expected_type: Expected type
            actual_type: Actual type
            **context: Additional context
        """
        message = (
            f"Invalid type for context key '{key}': "
            f"expected {expected_type.__name__}, got {actual_type.__name__}"
        )
        super().__init__(
            message,
            key=key,
            expected_type=expected_type.__name__,
            actual_type=actual_type.__name__,
            **context
        )
        self.key = key
        self.expected_type = expected_type
        self.actual_type = actual_type


# ============================================================================
# Helper Functions
# ============================================================================

def wrap_exception(exc: Exception, step_name: str) -> KernelError:
    """
    Wrap a generic exception in a kernel exception.

    Args:
        exc: Original exception
        step_name: Step name where exception occurred

    Returns:
        Wrapped kernel exception
    """
    if isinstance(exc, KernelError):
        return exc

    return StepExecutionError(
        step_name=step_name,
        cause=exc
    )


def log_exception(exc: Exception, level: str = "error") -> None:
    """
    Log an exception with appropriate level.

    Args:
        exc: Exception to log
        level: Log level (debug, info, warning, error, critical)
    """
    log_func = getattr(logger, level, logger.error)

    if isinstance(exc, KernelError):
        log_func(f"{exc.__class__.__name__}: {exc.message}")
        if exc.context:
            logger.debug(f"Context: {exc.context}")
    else:
        log_func(f"{exc.__class__.__name__}: {str(exc)}")
