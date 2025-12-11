from __future__ import annotations

import logging
from typing import Iterable, List, Sequence

from src.core_kernel.models import NormalizedRecord

log = logging.getLogger("dedupe")


def dedupe_records(records: Iterable[NormalizedRecord], key_fields: Sequence[str] = ("product_url", "name")) -> List[NormalizedRecord]:
    """Remove duplicate records based on the provided key fields.

    Args:
        records: Iterable of normalized records to inspect.
        key_fields: Field names used to build the deduplication key.

    Returns:
        List of ``NormalizedRecord`` items with only the first instance of each
        key tuple retained.

    Side effects:
        Logs a message for each dropped duplicate for observability.
    """

    seen = set()
    unique: List[NormalizedRecord] = []

    for record in records:
        try:
            key = tuple(record.get(field) if isinstance(record, dict) else getattr(record, field) for field in key_fields)
        except Exception as exc:  # pragma: no cover - defensive guard
            log.warning("Failed to compute dedupe key: %s", exc)
            unique.append(record)
            continue

        if key in seen:
            log.info("Dropping duplicate record", extra={"key": key})
            continue

        seen.add(key)
        unique.append(record)

    return unique
