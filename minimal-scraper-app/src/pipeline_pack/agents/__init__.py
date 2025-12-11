"""Agent package exposing registry and default agent registrations."""

from .base import Agent, AgentContext, BaseAgent
from .db_export_agent import DbExportAgent
from .html_parse_agent import HtmlParseAgent
from .http_fetch_agent import HttpFetchAgent
from .llm_normalizer_agent import LLMNormalizerAgent
from .pcid_match_agent import PCIDMatchAgent
from .qc_agent import QCAgent
from .registry import AgentRegistry, run_pipeline


def _register_default_agents() -> None:
    """Register built-in agents with the global registry."""

    AgentRegistry.register(HttpFetchAgent.name, HttpFetchAgent)
    AgentRegistry.register(HtmlParseAgent.name, HtmlParseAgent)
    AgentRegistry.register(LLMNormalizerAgent.name, LLMNormalizerAgent)
    AgentRegistry.register(QCAgent.name, QCAgent)
    AgentRegistry.register(PCIDMatchAgent.name, PCIDMatchAgent)
    AgentRegistry.register(DbExportAgent.name, DbExportAgent)


_register_default_agents()

__all__ = [
    "Agent",
    "AgentContext",
    "BaseAgent",
    "AgentRegistry",
    "run_pipeline",
    "HttpFetchAgent",
    "HtmlParseAgent",
    "LLMNormalizerAgent",
    "QCAgent",
    "PCIDMatchAgent",
    "DbExportAgent",
]
