# file: src/plugins/processors/normalize_llm_plugin.py
"""
Plugin wrapper for the LLM normalizer in src/processors/llm_normalizer.py.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.processors import llm_normalizer


def normalize_record(record: Dict[str, Any], llm_fn: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
    """
    Adapter wrapper that forwards to processors.llm_normalizer.normalize_record.
    """
    return llm_normalizer.normalize_record(record, llm_fn=llm_fn)
