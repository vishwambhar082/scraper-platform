from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from src.common.logging_utils import get_logger

log = get_logger("agents-llm")


@dataclass
class LLMRequest:
    messages: List[str]


class NoOpLLM:
    """Minimal LLM abstraction that simply echoes prompts.

    This avoids network calls while providing a deterministic interface that
    future implementations can replace.
    """

    model_name: str = "noop-llm"

    def generate(self, messages: Iterable[str]) -> str:
        msgs = list(messages)
        log.info("NoOpLLM called with %d messages", len(msgs))
        return " | ".join(msgs) if msgs else ""


__all__ = ["NoOpLLM", "LLMRequest"]
