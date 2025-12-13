"""Unified logging package with structured logging support."""

from src.app_logging.unified_logger import UnifiedLogger, get_unified_logger
from src.app_logging.structured_logger import (
    configure_structured_logging,
    get_structured_logger,
    get_global_structured_logger,
    setup_production_logging,
    setup_development_logging,
    StructuredUnifiedLogger,
)
from src.app_logging.log_context import (
    bind_context,
    unbind_context,
    clear_context,
    get_context,
    log_context,
    with_context_from_kwargs,
    context_scope,
    nested_context,
    isolated_context,
    RunContext,
    StepContext,
    TaskContext,
)

__all__ = [
    # Unified logger (existing)
    "UnifiedLogger",
    "get_unified_logger",
    # Structured logger
    "configure_structured_logging",
    "get_structured_logger",
    "get_global_structured_logger",
    "setup_production_logging",
    "setup_development_logging",
    "StructuredUnifiedLogger",
    # Context management
    "bind_context",
    "unbind_context",
    "clear_context",
    "get_context",
    "log_context",
    "with_context_from_kwargs",
    "context_scope",
    "nested_context",
    "isolated_context",
    "RunContext",
    "StepContext",
    "TaskContext",
]

