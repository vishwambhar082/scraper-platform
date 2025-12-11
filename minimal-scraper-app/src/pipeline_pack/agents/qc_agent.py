from __future__ import annotations

import logging

from .base import BaseAgent, AgentContext
from src.pipeline_pack.processors.qc_rules import default_qc_runner, QCRunner

logger = logging.getLogger(__name__)


class QCAgent(BaseAgent):
    name = "qc_rules"

    def execute(self, ctx: AgentContext) -> AgentContext:
        if not ctx.records:
            ctx.add_warning("QCAgent: no records for QC")
            return ctx

        runner: QCRunner
        if self.config.get("use_default", True):
            runner = default_qc_runner()
        else:
            runner = default_qc_runner()
        qc_result = runner.run(ctx.records)
        ctx.qc_results = qc_result
        return ctx


__all__ = ["QCAgent"]
