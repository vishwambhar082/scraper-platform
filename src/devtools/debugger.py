"""
Debugger Module

Provides debugging utilities for scraper development and troubleshooting.
Includes step-by-step execution, breakpoints, and inspection tools.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys

logger = logging.getLogger(__name__)


class DebugLevel(str, Enum):
    """Debug verbosity levels."""
    OFF = "off"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


class BreakpointCondition(str, Enum):
    """Breakpoint condition types."""
    ALWAYS = "always"
    ON_ERROR = "on_error"
    ON_VALUE = "on_value"
    ON_CHANGE = "on_change"
    CONDITIONAL = "conditional"


@dataclass
class Breakpoint:
    """Debugger breakpoint."""

    id: str
    location: str
    condition: BreakpointCondition = BreakpointCondition.ALWAYS
    condition_expr: Optional[str] = None
    enabled: bool = True
    hit_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def should_break(self, context: Dict[str, Any]) -> bool:
        """
        Check if breakpoint should trigger.

        Args:
            context: Execution context

        Returns:
            True if should break
        """
        if not self.enabled:
            return False

        if self.condition == BreakpointCondition.ALWAYS:
            return True

        if self.condition == BreakpointCondition.ON_ERROR:
            return context.get("has_error", False)

        if self.condition == BreakpointCondition.CONDITIONAL and self.condition_expr:
            try:
                return eval(self.condition_expr, {}, context)
            except Exception as e:
                logger.error(f"Breakpoint condition error: {e}")
                return False

        return False


@dataclass
class DebugFrame:
    """Debug stack frame."""

    function: str
    file: str
    line: int
    locals: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "function": self.function,
            "file": self.file,
            "line": self.line,
            "locals": {k: str(v) for k, v in self.locals.items()},
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DebugSnapshot:
    """Debug state snapshot."""

    timestamp: datetime
    step_name: str
    variables: Dict[str, Any]
    stack: List[DebugFrame]
    output: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "step_name": self.step_name,
            "variables": {k: str(v) for k, v in self.variables.items()},
            "stack": [f.to_dict() for f in self.stack],
            "output": str(self.output) if self.output else None,
            "error": self.error
        }


class ScraperDebugger:
    """
    Interactive debugger for scraper pipelines.

    Features:
    - Step-by-step execution
    - Breakpoints
    - Variable inspection
    - Stack traces
    - Execution history
    """

    def __init__(self, level: DebugLevel = DebugLevel.INFO):
        """
        Initialize debugger.

        Args:
            level: Debug verbosity level
        """
        self.level = level
        self.enabled = True
        self.breakpoints: Dict[str, Breakpoint] = {}
        self.snapshots: List[DebugSnapshot] = []
        self.step_mode = False
        self.current_step: Optional[str] = None
        logger.info(f"Initialized ScraperDebugger with level: {level.value}")

    def add_breakpoint(
        self,
        location: str,
        condition: BreakpointCondition = BreakpointCondition.ALWAYS,
        condition_expr: Optional[str] = None
    ) -> str:
        """
        Add a breakpoint.

        Args:
            location: Breakpoint location (step name, function, etc.)
            condition: Breakpoint condition
            condition_expr: Optional condition expression

        Returns:
            Breakpoint ID
        """
        bp_id = f"bp_{len(self.breakpoints)}"
        breakpoint = Breakpoint(
            id=bp_id,
            location=location,
            condition=condition,
            condition_expr=condition_expr
        )
        self.breakpoints[bp_id] = breakpoint
        logger.info(f"Added breakpoint: {location} ({condition.value})")
        return bp_id

    def remove_breakpoint(self, bp_id: str) -> bool:
        """
        Remove a breakpoint.

        Args:
            bp_id: Breakpoint ID

        Returns:
            True if removed
        """
        if bp_id in self.breakpoints:
            del self.breakpoints[bp_id]
            logger.info(f"Removed breakpoint: {bp_id}")
            return True
        return False

    def enable_step_mode(self) -> None:
        """Enable step-by-step execution."""
        self.step_mode = True
        logger.info("Step mode enabled")

    def disable_step_mode(self) -> None:
        """Disable step-by-step execution."""
        self.step_mode = False
        logger.info("Step mode disabled")

    def capture_snapshot(
        self,
        step_name: str,
        variables: Dict[str, Any],
        output: Optional[Any] = None,
        error: Optional[Exception] = None
    ) -> DebugSnapshot:
        """
        Capture execution snapshot.

        Args:
            step_name: Current step name
            variables: Current variables
            output: Step output
            error: Error if any

        Returns:
            Debug snapshot
        """
        # Capture stack trace
        stack = self._capture_stack()

        snapshot = DebugSnapshot(
            timestamp=datetime.now(),
            step_name=step_name,
            variables=variables.copy(),
            stack=stack,
            output=output,
            error=str(error) if error else None
        )

        self.snapshots.append(snapshot)
        logger.debug(f"Captured snapshot for step: {step_name}")

        return snapshot

    def _capture_stack(self) -> List[DebugFrame]:
        """Capture current call stack."""
        frames = []
        current_frame = sys._getframe(2)  # Skip this function and caller

        for _ in range(10):  # Limit stack depth
            if current_frame is None:
                break

            frame_info = DebugFrame(
                function=current_frame.f_code.co_name,
                file=current_frame.f_code.co_filename,
                line=current_frame.f_lineno,
                locals=current_frame.f_locals.copy()
            )
            frames.append(frame_info)

            current_frame = current_frame.f_back

        return frames

    def check_breakpoint(
        self,
        location: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if should break at location.

        Args:
            location: Current location
            context: Execution context

        Returns:
            True if should break
        """
        for bp in self.breakpoints.values():
            if bp.location == location and bp.should_break(context):
                bp.hit_count += 1
                logger.info(f"Breakpoint hit: {location} (hit count: {bp.hit_count})")
                return True

        return False

    def inspect_variable(self, var_name: str, value: Any) -> Dict[str, Any]:
        """
        Inspect a variable.

        Args:
            var_name: Variable name
            value: Variable value

        Returns:
            Variable inspection result
        """
        return {
            "name": var_name,
            "type": type(value).__name__,
            "value": str(value),
            "repr": repr(value),
            "size": sys.getsizeof(value),
            "is_none": value is None,
            "is_empty": not bool(value) if hasattr(value, '__bool__') else False
        }

    def trace_execution(
        self,
        step_name: str,
        inputs: Dict[str, Any],
        outputs: Optional[Any] = None,
        duration: Optional[float] = None
    ) -> None:
        """
        Trace execution of a step.

        Args:
            step_name: Step name
            inputs: Input variables
            outputs: Output value
            duration: Execution duration
        """
        if self.level == DebugLevel.OFF:
            return

        trace_msg = f"[TRACE] Step: {step_name}"

        if duration:
            trace_msg += f" | Duration: {duration:.3f}s"

        logger.debug(trace_msg)

        if self.level in {DebugLevel.DEBUG, DebugLevel.TRACE}:
            logger.debug(f"  Inputs: {inputs}")
            if outputs is not None:
                logger.debug(f"  Outputs: {outputs}")

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get execution history.

        Returns:
            List of snapshots
        """
        return [s.to_dict() for s in self.snapshots]

    def clear_history(self) -> None:
        """Clear execution history."""
        self.snapshots.clear()
        logger.info("Cleared execution history")

    def export_session(self) -> Dict[str, Any]:
        """
        Export debug session data.

        Returns:
            Session data
        """
        return {
            "level": self.level.value,
            "enabled": self.enabled,
            "step_mode": self.step_mode,
            "breakpoints": [
                {
                    "id": bp.id,
                    "location": bp.location,
                    "condition": bp.condition.value,
                    "hit_count": bp.hit_count
                }
                for bp in self.breakpoints.values()
            ],
            "snapshots": self.get_execution_history(),
            "snapshot_count": len(self.snapshots)
        }


class DebuggerContext:
    """Context manager for debugger sessions."""

    def __init__(self, debugger: ScraperDebugger, step_name: str):
        """
        Initialize debugger context.

        Args:
            debugger: Debugger instance
            step_name: Current step name
        """
        self.debugger = debugger
        self.step_name = step_name
        self.start_time = None
        self.variables: Dict[str, Any] = {}

    def __enter__(self):
        """Enter debug context."""
        self.start_time = datetime.now()
        self.debugger.current_step = self.step_name
        logger.debug(f"Entering debug context: {self.step_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit debug context."""
        duration = (datetime.now() - self.start_time).total_seconds()

        # Capture snapshot
        self.debugger.capture_snapshot(
            step_name=self.step_name,
            variables=self.variables,
            error=exc_val
        )

        # Trace execution
        self.debugger.trace_execution(
            step_name=self.step_name,
            inputs=self.variables,
            duration=duration
        )

        self.debugger.current_step = None
        logger.debug(f"Exiting debug context: {self.step_name}")

        return False  # Don't suppress exceptions


# Global debugger instance
_debugger: Optional[ScraperDebugger] = None


def get_debugger() -> ScraperDebugger:
    """
    Get the global debugger instance.

    Returns:
        Debugger singleton
    """
    global _debugger
    if _debugger is None:
        _debugger = ScraperDebugger()

    return _debugger


def debug_step(step_name: str) -> DebuggerContext:
    """
    Context manager for debugging a step.

    Args:
        step_name: Step name

    Returns:
        Debugger context
    """
    debugger = get_debugger()
    return DebuggerContext(debugger, step_name)
