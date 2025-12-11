"""
Completeness checks ensure required fields are present before export.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence


def check_required_fields(
    records: Iterable[Dict[str, object]], required_fields: Sequence[str]
) -> List[Dict[str, object]]:
    failures: List[Dict[str, object]] = []
    for record in records:
        missing = [field for field in required_fields if not record.get(field)]
        if missing:
            failures.append({"record": record, "missing": missing})
    return failures

