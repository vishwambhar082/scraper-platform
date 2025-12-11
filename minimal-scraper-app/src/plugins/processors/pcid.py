"""Plugin adapter for PCID matching helpers."""

from src.processors.pcid_matcher import build_pcid_index, match_records

__all__ = ["build_pcid_index", "match_records"]
