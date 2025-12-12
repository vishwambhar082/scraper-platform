"""Agent registry for agentic orchestrator."""

from __future__ import annotations

from typing import Callable, Dict, Iterable

from src.common.logging_utils import get_logger

from .base import BaseAgent

log = get_logger("agents.registry")


class AgentRegistry:
    """Maps agent names to agent factories or instances."""

    def __init__(self) -> None:
        self._agents: Dict[str, Callable[[], BaseAgent]] = {}

    def register(self, agent: BaseAgent | Callable[[], BaseAgent]) -> None:
        instance = agent if isinstance(agent, BaseAgent) else agent()
        if instance.name in self._agents:
            raise ValueError(f"Agent already registered: {instance.name}")
        # Store a factory so each fetch yields a fresh instance when needed
        self._agents[instance.name] = lambda a=instance: a
        log.debug("Registered agent %s", instance.name)

    def register_factory(self, name: str, factory: Callable[[], BaseAgent]) -> None:
        if name in self._agents:
            raise ValueError(f"Agent already registered: {name}")
        self._agents[name] = factory
        log.debug("Registered agent factory %s", name)

    def get(self, name: str) -> BaseAgent:
        try:
            factory = self._agents[name]
        except KeyError as exc:
            raise KeyError(f"Agent not found: {name}") from exc
        return factory()

    def list_agents(self) -> Dict[str, BaseAgent]:
        return {name: factory() for name, factory in self._agents.items()}

    def list_names(self) -> Iterable[str]:
        return self._agents.keys()


registry = AgentRegistry()


def register_builtin_agents() -> None:
    """Import built-in agents and register them once."""

    from src.agents.db_export_agent import DbExportAgent
    from src.agents.html_parse_agent import HtmlParseAgent
    from src.agents.http_agent import HttpFetchAgent

    for agent_cls in (HttpFetchAgent, HtmlParseAgent, DbExportAgent):
        try:
            registry.register_factory(agent_cls.__name__, agent_cls)
        except ValueError:
            # Already registered in tests or earlier imports
            continue


__all__ = ["AgentRegistry", "registry", "register_builtin_agents"]
