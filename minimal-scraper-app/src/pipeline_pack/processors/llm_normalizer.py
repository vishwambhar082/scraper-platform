from __future__ import annotations

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LLMNormalizer:
    """Stub normalizer – replace with actual LLM calls as needed."""

    def __init__(self, model: str, system_prompt: str) -> None:
        self.model = model
        self.system_prompt = system_prompt

    def normalize_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info("LLMNormalizer: pretending to normalize %s records", len(records))
        return records


__all__ = ["LLMNormalizer"]
