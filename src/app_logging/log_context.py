"""
Thread-local context management for structured logging.

This module provides thread-safe context storage and management for
structured logging. Context variables are automatically included in
all log entries within the same thread.

Features:
- Thread-local context storage
- Context binding/unbinding
- Context decorators for automatic management
- Integration with structlog contextvars
- Support for nested contexts
- Context managers for scoped contexts
"""

from __future__ import annotations

import functools
import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional, TypeVar

import structlog


# Thread-local storage for context
_thread_local = threading.local()


# Type variable for decorator return types
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Core Context Management
# ============================================================================

def get_context() -> Dict[str, Any]:
    """
    Get the current thread's logging context.

    Returns:
        Dictionary of context variables for the current thread

    Example:
        context = get_context()
        print(context.get("run_id"))
    """
    if not hasattr(_thread_local, "context"):
        _thread_local.context = {}
    return _thread_local.context


def set_context(context: Dict[str, Any]) -> None:
    """
    Replace the current thread's logging context.

    Args:
        context: New context dictionary

    Example:
        set_context({"run_id": "12345", "source": "alfabeta"})
    """
    _thread_local.context = context.copy()

    # Also update structlog contextvars
    structlog.contextvars.clear_contextvars()
    if context:
        structlog.contextvars.bind_contextvars(**context)


def clear_context() -> None:
    """
    Clear all context variables for the current thread.

    Example:
        clear_context()
    """
    _thread_local.context = {}
    structlog.contextvars.clear_contextvars()


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables to the current thread.

    These variables will be automatically included in all log entries
    for the current thread.

    Args:
        **kwargs: Context variables to bind

    Example:
        bind_context(run_id="12345", source="alfabeta")
        log.info("step_started")  # Automatically includes run_id and source
    """
    context = get_context()
    context.update(kwargs)

    # Also update structlog contextvars
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """
    Remove specific context variables from the current thread.

    Args:
        *keys: Keys to remove from context

    Example:
        unbind_context("run_id", "source")
    """
    context = get_context()
    for key in keys:
        context.pop(key, None)

    # Also update structlog contextvars
    structlog.contextvars.unbind_contextvars(*keys)


def merge_context(**kwargs: Any) -> Dict[str, Any]:
    """
    Get a merged context dictionary without modifying the thread context.

    Useful for one-time context additions without permanently binding.

    Args:
        **kwargs: Temporary context variables to merge

    Returns:
        Merged context dictionary

    Example:
        context = merge_context(step_id="step_1")
        log.info("step started", **context)
    """
    context = get_context().copy()
    context.update(kwargs)
    return context


# ============================================================================
# Context Decorators
# ============================================================================

def log_context(**context_vars: Any) -> Callable[[F], F]:
    """
    Decorator to automatically bind context variables for the duration of a function.

    Context is automatically cleared when the function exits.

    Args:
        **context_vars: Context variables to bind

    Example:
        @log_context(source="alfabeta", job_id="daily_scrape")
        def scrape_alfabeta():
            log.info("scrape_started")  # Includes source and job_id
            # ... scraping logic ...
            log.info("scrape_completed")  # Also includes source and job_id
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Save current context
            original_context = get_context().copy()

            try:
                # Bind new context
                bind_context(**context_vars)

                # Execute function
                return func(*args, **kwargs)
            finally:
                # Restore original context
                set_context(original_context)

        return wrapper  # type: ignore

    return decorator


def inherit_context(func: F) -> F:
    """
    Decorator to ensure context is inherited from parent thread/context.

    Useful for async/threaded operations where context might not
    automatically propagate.

    Args:
        func: Function to decorate

    Example:
        @inherit_context
        def background_task():
            log.info("task_started")  # Inherits context from parent
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Context is already in thread-local storage, just execute
        return func(*args, **kwargs)

    return wrapper  # type: ignore


def with_context_from_kwargs(*context_keys: str) -> Callable[[F], F]:
    """
    Decorator to bind context variables from function keyword arguments.

    Specified kwargs will be added to the logging context for the
    duration of the function.

    Args:
        *context_keys: Names of kwargs to bind as context

    Example:
        @with_context_from_kwargs("run_id", "source")
        def process_scrape(run_id: str, source: str, data: dict):
            log.info("processing")  # Includes run_id and source
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract context from kwargs
            context = {key: kwargs[key] for key in context_keys if key in kwargs}

            # Save current context
            original_context = get_context().copy()

            try:
                # Bind context from kwargs
                if context:
                    bind_context(**context)

                # Execute function
                return func(*args, **kwargs)
            finally:
                # Restore original context
                set_context(original_context)

        return wrapper  # type: ignore

    return decorator


# ============================================================================
# Context Managers
# ============================================================================

@contextmanager
def context_scope(**context_vars: Any) -> Generator[None, None, None]:
    """
    Context manager to temporarily bind context variables.

    Context is automatically cleared when exiting the scope.

    Args:
        **context_vars: Context variables to bind

    Example:
        with context_scope(run_id="12345", source="alfabeta"):
            log.info("step_started")  # Includes run_id and source
            # ... processing ...
            log.info("step_completed")  # Also includes context

        log.info("outside_scope")  # Context is cleared
    """
    # Save current context
    original_context = get_context().copy()

    try:
        # Bind new context
        bind_context(**context_vars)
        yield
    finally:
        # Restore original context
        set_context(original_context)


@contextmanager
def nested_context(**context_vars: Any) -> Generator[None, None, None]:
    """
    Context manager that adds to existing context without clearing it.

    Useful for adding temporary context while preserving parent context.

    Args:
        **context_vars: Context variables to add

    Example:
        bind_context(run_id="12345")

        with nested_context(step_id="step_1"):
            log.info("step_started")  # Includes run_id AND step_id

        log.info("between_steps")  # Only includes run_id

        with nested_context(step_id="step_2"):
            log.info("step_started")  # Includes run_id AND step_id (updated)
    """
    # Save keys to unbind later
    keys_to_unbind = list(context_vars.keys())

    try:
        # Add to existing context
        bind_context(**context_vars)
        yield
    finally:
        # Remove only the keys we added
        unbind_context(*keys_to_unbind)


@contextmanager
def isolated_context(**context_vars: Any) -> Generator[None, None, None]:
    """
    Context manager that completely isolates context from parent scope.

    Starts with a clean context, ignoring parent context.

    Args:
        **context_vars: Context variables for isolated scope

    Example:
        bind_context(run_id="12345", source="alfabeta")

        with isolated_context(task_id="task_1"):
            log.info("isolated_task")  # Only includes task_id, not run_id or source

        log.info("back_to_parent")  # Includes run_id and source again
    """
    # Save current context
    original_context = get_context().copy()

    try:
        # Start with clean context
        clear_context()

        # Bind new context
        if context_vars:
            bind_context(**context_vars)

        yield
    finally:
        # Restore original context
        set_context(original_context)


# ============================================================================
# Specialized Context Helpers
# ============================================================================

class RunContext:
    """
    Specialized context manager for scraping runs.

    Automatically manages run_id, source, and other run-specific context.

    Example:
        with RunContext(run_id="12345", source="alfabeta"):
            log.info("run_started")
            # ... scraping logic ...
            log.info("run_completed")
    """

    def __init__(
        self,
        run_id: str,
        source: Optional[str] = None,
        job_id: Optional[str] = None,
        environment: Optional[str] = None,
        **extra_context: Any,
    ):
        """
        Initialize run context.

        Args:
            run_id: Unique run identifier
            source: Source being scraped
            job_id: Job identifier
            environment: Environment (dev, staging, prod)
            **extra_context: Additional context variables
        """
        self.context_vars = {"run_id": run_id}

        if source:
            self.context_vars["source"] = source
        if job_id:
            self.context_vars["job_id"] = job_id
        if environment:
            self.context_vars["environment"] = environment

        self.context_vars.update(extra_context)
        self.original_context: Dict[str, Any] = {}

    def __enter__(self) -> RunContext:
        """Enter the run context."""
        self.original_context = get_context().copy()
        bind_context(**self.context_vars)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the run context."""
        set_context(self.original_context)


class StepContext:
    """
    Specialized context manager for pipeline steps.

    Automatically manages step_id and step-specific context.

    Example:
        with StepContext(step_id="fetch_data", step_type="FETCH"):
            log.info("step_started")
            # ... step logic ...
            log.info("step_completed")
    """

    def __init__(
        self,
        step_id: str,
        step_type: Optional[str] = None,
        step_index: Optional[int] = None,
        **extra_context: Any,
    ):
        """
        Initialize step context.

        Args:
            step_id: Unique step identifier
            step_type: Type of step (FETCH, PARSE, etc.)
            step_index: Step index in pipeline
            **extra_context: Additional context variables
        """
        self.context_vars = {"step_id": step_id}

        if step_type:
            self.context_vars["step_type"] = step_type
        if step_index is not None:
            self.context_vars["step_index"] = step_index

        self.context_vars.update(extra_context)
        self.keys_to_unbind = list(self.context_vars.keys())

    def __enter__(self) -> StepContext:
        """Enter the step context."""
        bind_context(**self.context_vars)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the step context."""
        unbind_context(*self.keys_to_unbind)


class TaskContext:
    """
    Specialized context manager for tasks.

    Automatically manages task_id and task-specific context.

    Example:
        with TaskContext(task_id="scrape_alfabeta", task_type="scraping"):
            log.info("task_started")
            # ... task logic ...
            log.info("task_completed")
    """

    def __init__(
        self,
        task_id: str,
        task_type: Optional[str] = None,
        **extra_context: Any,
    ):
        """
        Initialize task context.

        Args:
            task_id: Unique task identifier
            task_type: Type of task
            **extra_context: Additional context variables
        """
        self.context_vars = {"task_id": task_id}

        if task_type:
            self.context_vars["task_type"] = task_type

        self.context_vars.update(extra_context)
        self.keys_to_unbind = list(self.context_vars.keys())

    def __enter__(self) -> TaskContext:
        """Enter the task context."""
        bind_context(**self.context_vars)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the task context."""
        unbind_context(*self.keys_to_unbind)


# ============================================================================
# Utility Functions
# ============================================================================

def get_run_id() -> Optional[str]:
    """
    Get the current run_id from context.

    Returns:
        Current run_id or None if not set

    Example:
        run_id = get_run_id()
    """
    return get_context().get("run_id")


def get_source() -> Optional[str]:
    """
    Get the current source from context.

    Returns:
        Current source or None if not set

    Example:
        source = get_source()
    """
    return get_context().get("source")


def get_step_id() -> Optional[str]:
    """
    Get the current step_id from context.

    Returns:
        Current step_id or None if not set

    Example:
        step_id = get_step_id()
    """
    return get_context().get("step_id")


def get_task_id() -> Optional[str]:
    """
    Get the current task_id from context.

    Returns:
        Current task_id or None if not set

    Example:
        task_id = get_task_id()
    """
    return get_context().get("task_id")


def get_job_id() -> Optional[str]:
    """
    Get the current job_id from context.

    Returns:
        Current job_id or None if not set

    Example:
        job_id = get_job_id()
    """
    return get_context().get("job_id")


def has_context(*keys: str) -> bool:
    """
    Check if all specified keys exist in the current context.

    Args:
        *keys: Keys to check

    Returns:
        True if all keys exist in context

    Example:
        if has_context("run_id", "source"):
            # Both run_id and source are set
            pass
    """
    context = get_context()
    return all(key in context for key in keys)


def copy_context() -> Dict[str, Any]:
    """
    Get a copy of the current context.

    Returns:
        Copy of current context dictionary

    Example:
        context_snapshot = copy_context()
    """
    return get_context().copy()
