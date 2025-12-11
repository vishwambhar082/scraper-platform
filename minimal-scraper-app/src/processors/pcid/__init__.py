# file: src/processors/pcid/__init__.py
"""
PCID (Product Code ID) matching and vector store integration.
"""

from __future__ import annotations

from .pcid_matching import (
    PcidMatchResult,
    PcidVectorStore,
    build_pcid_query_text,
    match_pcid_batch,
    match_pcid_for_record,
)

__all__ = [
    "PcidMatchResult",
    "PcidVectorStore",
    "build_pcid_query_text",
    "match_pcid_batch",
    "match_pcid_for_record",
]

