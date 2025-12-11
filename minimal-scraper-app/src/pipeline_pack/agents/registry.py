from __future__ import annotations

from typing import Type, Dict, Any, List
import logging

from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Global registry for agents, enabling config-driven construction.
    """

    _registry: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_cls: Type[BaseAgent]) -> None:
        if name in cls._registry:
            logger.warning("Overriding existing agent registration for %s", name)
        cls._registry[name] = agent_cls
        logger.debug("Registered agent '%s' -> %s", name, agent_cls.__name__)

    @classmethod
    def build(cls, name: str, **kwargs: Any) -> BaseAgent:
        if name not in cls._registry:
            raise ValueError(f"Agent '{name}' is not registered")
        agent_cls = cls._registry[name]
        return agent_cls(**kwargs)

    @classmethod
    def list_agents(cls) -> List[str]:
        return sorted(cls._registry.keys())


def run_pipeline(
    pipeline: list[dict[str, Any]],
    ctx: AgentContext,
    default_agent_config: dict[str, Any] | None = None,
) -> AgentContext:
    """Execute pipeline steps defined as a list of agent descriptors."""

    default_agent_config = default_agent_config or {}
    for step in pipeline:
        agent_name = step.get("name") or step.get("agent")
        cfg = {**default_agent_config, **step.get("config", {})}
        agent = AgentRegistry.build(agent_name, **cfg)
        logger.info("Running pipeline step: %s", agent_name)
        ctx = agent.run(ctx)
    return ctx


__all__ = ["AgentRegistry", "run_pipeline"]
