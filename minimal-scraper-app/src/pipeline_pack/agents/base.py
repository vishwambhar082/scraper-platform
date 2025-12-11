from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
import logging
import uuid
import time

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """
    Shared context object passed between agents in a pipeline.

    This holds typical scrape state such as:
    - input parameters (source, env, run_id, etc.)
    - transient state (html, json_data, records)
    - error and warning collections
    - timing metadata for simple observability
    """

    source: str
    env: str = "dev"
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    request: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)

    html: Optional[str] = None
    json_data: Optional[Dict[str, Any]] = None
    records: List[Dict[str, Any]] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    qc_results: Dict[str, Any] = field(default_factory=dict)
    pcid_matches: List[Dict[str, Any]] = field(default_factory=list)
    export_summary: Dict[str, Any] = field(default_factory=dict)

    timings: Dict[str, float] = field(default_factory=dict)

    def add_error(self, msg: str) -> None:
        logger.error("[run_id=%s] %s", self.run_id, msg)
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        logger.warning("[run_id=%s] %s", self.run_id, msg)
        self.warnings.append(msg)

    def mark_timing(self, key: str, start_time: float) -> None:
        self.timings[key] = time.time() - start_time


@runtime_checkable
class Agent(Protocol):
    """Protocol for pluggable agents."""

    name: str

    def run(self, ctx: AgentContext) -> AgentContext:
        ...


class BaseAgent:
    """Minimal base class offering before/after hooks and timing."""

    name: str = "base_agent"

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs

    def before_run(self, ctx: AgentContext) -> None:  # pragma: no cover - hook
        logger.debug("[%s] before_run ctx.run_id=%s", self.name, ctx.run_id)

    def execute(self, ctx: AgentContext) -> AgentContext:
        """Override in subclasses with the main work."""

        raise NotImplementedError

    def after_run(self, ctx: AgentContext) -> None:  # pragma: no cover - hook
        logger.debug("[%s] after_run ctx.run_id=%s", self.name, ctx.run_id)

    def run(self, ctx: AgentContext) -> AgentContext:
        logger.info(
            "[%s] Starting agent for source=%s env=%s run_id=%s",
            self.name,
            ctx.source,
            ctx.env,
            ctx.run_id,
        )
        start = time.time()
        self.before_run(ctx)
        try:
            ctx = self.execute(ctx)
        except Exception as exc:  # pragma: no cover - runtime guard
            msg = f"Agent {self.name} failed: {exc!r}"
            logger.exception(msg)
            ctx.add_error(msg)
        self.after_run(ctx)
        ctx.mark_timing(self.name, start)
        logger.info(
            "[%s] Completed agent in %.3fs (run_id=%s)",
            self.name,
            ctx.timings.get(self.name, 0.0),
            ctx.run_id,
        )
        return ctx


__all__ = ["AgentContext", "Agent", "BaseAgent"]
