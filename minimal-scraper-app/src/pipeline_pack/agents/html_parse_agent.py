from __future__ import annotations

from typing import Any, Dict, List
import logging
from bs4 import BeautifulSoup

from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class HtmlParseAgent(BaseAgent):
    name = "html_parse"

    def execute(self, ctx: AgentContext) -> AgentContext:
        if not ctx.html:
            ctx.add_warning("HtmlParseAgent: ctx.html is empty")
            return ctx

        selectors: Dict[str, Any] = self.config.get("selectors", {})
        soup = BeautifulSoup(ctx.html, "lxml")
        records: List[Dict[str, Any]] = []

        list_sel = selectors.get("list")
        fields = selectors.get("fields", {})
        items = soup.select(list_sel) if list_sel else [soup]

        for item in items:
            rec: Dict[str, Any] = {}
            for field_name, sel_cfg in fields.items():
                css = sel_cfg.get("css")
                attr = sel_cfg.get("attr")
                default = sel_cfg.get("default", "").strip()
                val = default
                if css:
                    node = item.select_one(css)
                    if node:
                        if attr:
                            val = node.get(attr, default)
                        else:
                            val = node.get_text(strip=True)
                rec[field_name] = val
            records.append(rec)

        ctx.records = records
        return ctx


__all__ = ["HtmlParseAgent"]
