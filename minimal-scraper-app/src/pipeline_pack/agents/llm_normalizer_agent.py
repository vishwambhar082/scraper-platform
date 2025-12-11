from __future__ import annotations

import logging

from .base import BaseAgent, AgentContext
from src.pipeline_pack.processors.llm_normalizer import LLMNormalizer

logger = logging.getLogger(__name__)


class LLMNormalizerAgent(BaseAgent):
    name = "llm_normalizer"

    def execute(self, ctx: AgentContext) -> AgentContext:
        if not ctx.records:
            ctx.add_warning("LLMNormalizerAgent: no records to normalize")
            return ctx

        model = self.config.get("model", "gpt-4.1-mini")
        system_prompt = self.config.get("system_prompt", "Normalize fields.")
        normalizer = LLMNormalizer(model=model, system_prompt=system_prompt)
        normalized = normalizer.normalize_records(ctx.records)
        ctx.records = normalized
        return ctx


__all__ = ["LLMNormalizerAgent"]
