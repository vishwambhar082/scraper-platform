"""Composable agent framework with registry and orchestration helpers.

This module provides lightweight primitives for building agentic pipelines:

* :class:`AgentContext` carries run metadata and shared mutable state.
* :class:`BaseAgent` standardizes inputs/outputs for reusable agent steps.
* :class:`AgentRegistry` registers agent instances for orchestration.
* :class:`AgentOrchestrator` executes registered agents in sequence.

An example pipeline for a concrete scraper source is provided at the bottom of
this file to illustrate how the pieces fit together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, MutableMapping, Optional

from src.agents.agent_orchestrator import load_recent_output_counts
from src.agents.deepagent_repair_engine import run_repair_session
from src.agents.replay_validator import ReplayFailure, validate_replay_results
from src.agents.scraper_brain import assess_source_health
from src.common.logging_utils import get_logger

log = get_logger("agent-framework")


@dataclass
class AgentContext:
    """Shared runtime context passed between agents during orchestration."""

    run_id: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    shared_state: MutableMapping[str, Any] = field(default_factory=dict)
    artifacts: MutableMapping[str, Any] = field(default_factory=dict)

    def with_updates(
        self,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        shared_state: Optional[MutableMapping[str, Any]] = None,
        artifacts: Optional[MutableMapping[str, Any]] = None,
    ) -> "AgentContext":
        """Return a shallow copy of the context with updated mappings."""

        return AgentContext(
            run_id=self.run_id,
            source=self.source,
            metadata={**self.metadata, **(metadata or {})},
            shared_state=shared_state or self.shared_state,
            artifacts=artifacts or self.artifacts,
        )


@dataclass
class AgentResult:
    """Standardized agent response used by the orchestrator."""

    agent_name: str
    succeeded: bool
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    continue_pipeline: bool = True


class BaseAgent:
    """Base class for deterministic agent steps."""

    name: str

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or self.__class__.__name__

    def run(self, context: AgentContext) -> AgentResult:  # pragma: no cover - abstract
        raise NotImplementedError


class AgentRegistry:
    """Registry of agent instances by name."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent already registered: {agent.name}")
        self._agents[agent.name] = agent
        log.debug("Registered agent %s", agent.name)

    def get(self, name: str) -> BaseAgent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(f"Agent not found: {name}") from exc

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)

    def list_names(self) -> List[str]:
        return list(self._agents.keys())


class AgentOrchestrator:
    """Executes registered agents in order using a shared context."""

    def __init__(self, registry: AgentRegistry, steps: Optional[Iterable[str]] = None) -> None:
        self.registry = registry
        self.steps: List[str] = list(steps or [])

    def add_step(self, agent_name: str) -> None:
        if agent_name not in self.registry.list_names():
            raise ValueError(f"Agent '{agent_name}' is not registered")
        self.steps.append(agent_name)

    def run(self, context: AgentContext) -> List[AgentResult]:
        results: List[AgentResult] = []
        log.info("Starting orchestration for source=%s run_id=%s", context.source, context.run_id)

        for agent_name in self.steps:
            agent = self.registry.get(agent_name)
            log.debug("Running agent %s", agent.name)
            result = agent.run(context)
            results.append(result)
            context.shared_state[agent_name] = result.data

            if not result.continue_pipeline:
                log.info("Stopping pipeline after %s (continue_pipeline=False)", agent.name)
                break

        log.info("Orchestration complete for source=%s run_id=%s", context.source, context.run_id)
        return results


# --- Example pipeline wiring for a specific source ---


class VolumeDriftAgent(BaseAgent):
    """Detects volume drift for a source using historical CSV counts."""

    def run(self, context: AgentContext) -> AgentResult:
        counts = load_recent_output_counts(context.source, limit=2)
        current_rows = counts[0] if counts else 0
        baseline_rows = counts[1] if len(counts) > 1 else current_rows

        assessment = assess_source_health(context.source, baseline_rows, current_rows)
        summary = f"volume={current_rows}, baseline={baseline_rows}, action={assessment.drift_decision.action}"
        context.shared_state["assessment"] = assessment

        return AgentResult(
            agent_name=self.name,
            succeeded=True,
            summary=summary,
            data={"assessment": assessment},
            continue_pipeline=assessment.drift_decision.action != "noop",
        )


class SelectorRepairAgent(BaseAgent):
    """Triggers the DeepAgent repair loop when drift is detected."""

    def __init__(self, selectors_path: Optional[str] = None) -> None:
        super().__init__()
        self.selectors_path = selectors_path

    def run(self, context: AgentContext) -> AgentResult:
        patches = run_repair_session(context.source, selectors_path=self.selectors_path)
        summary = "repair_session=triggered" if patches else "repair_session=no_patches"
        context.artifacts["patches"] = patches

        return AgentResult(
            agent_name=self.name,
            succeeded=True,
            summary=summary,
            data={"patches": patches},
            continue_pipeline=bool(patches),
        )


class ReplayValidationAgent(BaseAgent):
    """Validates replay results after selector repairs."""

    def __init__(self, replay_results: Optional[Iterable[bool]] = None) -> None:
        super().__init__()
        self.replay_results = replay_results

    def run(self, context: AgentContext) -> AgentResult:
        results = self.replay_results or context.artifacts.get("replay_results") or []
        try:
            validate_replay_results(results)
            summary = "replay_validated"
            succeeded = True
        except ReplayFailure as exc:
            summary = f"replay_failed: {exc}"
            succeeded = False

        return AgentResult(
            agent_name=self.name,
            succeeded=succeeded,
            summary=summary,
            data={"replay_results": list(results)},
            continue_pipeline=succeeded,
        )


def build_example_news_pipeline(run_id: str, source: str) -> AgentOrchestrator:
    """Return an orchestrator pre-wired for a news source auto-heal flow."""

    context = AgentContext(run_id=run_id, source=source)

    registry = AgentRegistry()
    registry.register(VolumeDriftAgent())
    registry.register(SelectorRepairAgent())
    registry.register(ReplayValidationAgent())

    orchestrator = AgentOrchestrator(registry, steps=["VolumeDriftAgent", "SelectorRepairAgent", "ReplayValidationAgent"])

    # Attach context to orchestrator for convenience when used as a callable.
    orchestrator.context = context  # type: ignore[attr-defined]
    return orchestrator


__all__ = [
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "AgentRegistry",
    "AgentOrchestrator",
    "VolumeDriftAgent",
    "SelectorRepairAgent",
    "ReplayValidationAgent",
    "build_example_news_pipeline",
]
