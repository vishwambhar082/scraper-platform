# file: src/processors/llm/dspy_normalizer.py
"""
Thin wrapper over src/processors/llm_normalizer.py so the v5.0
layout has a stable import path.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.processors import llm_normalizer


def normalize_record(record: Dict[str, Any], llm_fn: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
    """
    Delegate to the core llm_normalizer.normalize_record, preserving the same signature.
    """
    return llm_normalizer.normalize_record(record, llm_fn=llm_fn)
