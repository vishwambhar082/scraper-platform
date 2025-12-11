"""HTML parsing agent using BeautifulSoup."""
from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup

from src.common.logging_utils import get_logger

from .base import AgentConfig, AgentContext, BaseAgent

log = get_logger("agents.html-parse")


class HtmlParseAgent(BaseAgent):
    """Parse HTML stored in the context and expose a BeautifulSoup object."""

    def __init__(self, *, config: Optional[AgentConfig] = None) -> None:
        super().__init__(config=config)

    def run(self, context: AgentContext) -> AgentContext:
        html = context.get("raw_html")
        if not html:
            raise ValueError("HtmlParseAgent requires 'raw_html' in context")

        soup = BeautifulSoup(html, "lxml")
        context["parsed_html"] = soup
        title = soup.title.string if soup.title else None
        if title:
            context.metadata.setdefault("page", {})["title"] = title
        return context


__all__ = ["HtmlParseAgent"]
