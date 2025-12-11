"""
Deduplicate records based on a configurable key.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence


def dedupe_by_keys(records: Iterable[Dict[str, object]], keys: Sequence[str]) -> List[Dict[str, object]]:
    seen: set[tuple] = set()
    deduped: List[Dict[str, object]] = []
    for record in records:
        signature = tuple(record.get(key) for key in keys)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(record)
    return deduped

