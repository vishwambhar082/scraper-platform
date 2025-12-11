from __future__ import annotations

from typing import Any, Dict, List
import logging

from .base import BaseAgent, AgentContext
from src.pipeline_pack.processors.pcid_matcher import PCIDMatcher

logger = logging.getLogger(__name__)


class PCIDMatchAgent(BaseAgent):
    name = "pcid_match"

    def execute(self, ctx: AgentContext) -> AgentContext:
        if not ctx.records:
            ctx.add_warning("PCIDMatchAgent: no records to match")
            return ctx

        master_records: List[Dict[str, Any]] = self.config.get("master_records", [])
        matcher = PCIDMatcher(master_records)
        matches = matcher.match_records(ctx.records)
        ctx.pcid_matches = matches

        if self.config.get("attach_to_records", True):
            for rec, match in zip(ctx.records, matches):
                rec["pcid"] = match.get("pcid")
                rec["pcid_confidence"] = match.get("confidence")
        return ctx


__all__ = ["PCIDMatchAgent"]
