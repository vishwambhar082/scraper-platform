"""
Core execution engine for desktop application.

This module provides the single authoritative execution engine that replaces
fragmented runners and provides unified control over all pipeline executions.
"""

from .core_engine import CoreExecutionEngine, ExecutionContext, ExecutionState
from .checkpoint import CheckpointManager
from .resource_monitor import ResourceMonitor

__all__ = [
    'CoreExecutionEngine',
    'ExecutionContext',
    'ExecutionState',
    'CheckpointManager',
    'ResourceMonitor',
]
