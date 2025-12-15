"""Unified agent base classes consolidating src/agents and src/pipeline_pack/agents."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from src.common.logging_utils import get_logger

log = get_logger("agents.unified")


@dataclass
class UnifiedAgentContext:
    """Unified context combining features from both agent implementations."""

    # Core identification
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    environment: str = "dev"

    # Request/Response
    request: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)

    # Data state
    html: Optional[str] = None
    json_data: Optional[Dict[str, Any]] = None
    records: List[Dict[str, Any]] = field(default_factory=list)

    # Processing results
    qc_results: Dict[str, Any] = field(default_factory=dict)
    pcid_matches: List[Dict[str, Any]] = field(default_factory=list)
    export_summary: Dict[str, Any] = field(default_factory=dict)

    # Metadata and state
    metadata: Dict[str, Any] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)

    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Performance tracking
    timings: Dict[str, float] = field(default_factory=dict)

    # Dict-like access for compatibility
    _data: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def get_nested(self, path: str, default: Any = None) -> Any:
        """Get nested value using dot notation."""
        current = self._data
        for part in path.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return default
        return current

    def set_nested(self, path: str, value: Any) -> None:
        """Set nested value using dot notation."""
        parts = path.split(".")
        current = self._data
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def merge(self, other: Mapping[str, Any], overwrite: bool = True) -> None:
        """Merge another mapping into this context."""
        for key, value in other.items():
            if overwrite or key not in self._data:
                self._data[key] = value

    def copy(self) -> UnifiedAgentContext:
        """Create a copy of this context."""
        import copy

        return copy.deepcopy(self)

    def add_error(self, msg: str) -> None:
        """Add an error message."""
        log.error("[run_id=%s] %s", self.run_id, msg)
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        """Add a warning message."""
        log.warning("[run_id=%s] %s", self.run_id, msg)
        self.warnings.append(msg)

    def mark_timing(self, key: str, start_time: float) -> None:
        """Record timing for an operation."""
        self.timings[key] = time.time() - start_time


class UnifiedAgentBase:
    """Unified base agent class."""

    name: str = "base_agent"

    def __init__(self, name: Optional[str] = None, **config: Any) -> None:
        self.name = name or self.__class__.__name__
        self.config = config

    def before_run(self, ctx: UnifiedAgentContext) -> None:
        """Hook called before execute."""
        log.debug("[%s] before_run run_id=%s", self.name, ctx.run_id)

    def execute(self, ctx: UnifiedAgentContext) -> UnifiedAgentContext:
        """Main execution logic - override in subclasses."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement execute()")

    def after_run(self, ctx: UnifiedAgentContext) -> None:
        """Hook called after execute."""
        log.debug("[%s] after_run run_id=%s", self.name, ctx.run_id)

    def run(self, ctx: UnifiedAgentContext) -> UnifiedAgentContext:
        """Execute the agent with timing and error handling."""
        log.info(
            "[%s] Starting agent for source=%s env=%s run_id=%s",
            self.name,
            ctx.source,
            ctx.environment,
            ctx.run_id,
        )

        start = time.time()
        self.before_run(ctx)

        try:
            ctx = self.execute(ctx)
        except Exception as exc:
            msg = f"Agent {self.name} failed: {exc!r}"
            log.exception(msg)
            ctx.add_error(msg)

        self.after_run(ctx)
        ctx.mark_timing(self.name, start)

        log.info(
            "[%s] Completed in %.3fs (run_id=%s)",
            self.name,
            ctx.timings.get(self.name, 0.0),
            ctx.run_id,
        )

        return ctx


__all__ = ["UnifiedAgentContext", "UnifiedAgentBase"]
