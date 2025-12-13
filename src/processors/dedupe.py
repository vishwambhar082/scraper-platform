"""
Dedupe compatibility wrapper.

Imports from src.processors.qc.dedupe for actual implementation.
This file exists only for backward compatibility with existing scrapers.
"""
from __future__ import annotations

from typing import Iterable, List, Sequence
from src.common.types import NormalizedRecord
from src.processors.qc.dedupe import dedupe_records as _dedupe_with_info


def dedupe_records(
    records: Iterable[NormalizedRecord],
    key_fields: Sequence[str] = ("product_url", "name")
) -> List[NormalizedRecord]:
    """
    Remove duplicate records based on key fields.

    This is a compatibility wrapper around src.processors.qc.dedupe.dedupe_records
    that discards the duplicate metadata and returns only unique records.

    Args:
        records: Iterable of normalized records
        key_fields: Fields to use for deduplication key

    Returns:
        List of unique records (first occurrence wins)
    """
    unique, _dup_info = _dedupe_with_info(records, key_fields)
    return unique


__all__ = ["dedupe_records"]
