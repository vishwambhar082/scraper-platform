"""
Deduplication helpers.

This is intentionally separate from QC rules so that:
    - you can run QC on *all* records
    - then dedupe only the ones that passed QC

Dedupe is based on a configurable composite key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from . import validators


Record = Dict[str, Any]


@dataclass
class DuplicateInfo:
    key: Tuple[Any, ...]
    kept_index: int
    duplicate_index: int
    reason: str


def dedupe_records(
    records: Iterable[Record],
    key_fields: Sequence[str],
) -> Tuple[List[Record], List[DuplicateInfo]]:
    """
    Deduplicate records based on a composite key built from `key_fields`.

    Returns:
        (unique_records, duplicates_info)

    - unique_records: list of records we keep (first occurrence wins)
    - duplicates_info: metadata about what was dropped and why
    """
    seen: Dict[Tuple[Any, ...], int] = {}
    unique: List[Record] = []
    dup_info: List[DuplicateInfo] = []

    for idx, rec in enumerate(records):
        key = validators.build_dedupe_key(rec, key_fields)
        if key in seen:
            kept_idx = seen[key]
            dup_info.append(
                DuplicateInfo(
                    key=key,
                    kept_index=kept_idx,
                    duplicate_index=len(unique) + len(dup_info),
                    reason=f"duplicate key on fields {key_fields}",
                )
            )
            # do not append this record
            continue

        seen[key] = idx
        unique.append(rec)

    return unique, dup_info
