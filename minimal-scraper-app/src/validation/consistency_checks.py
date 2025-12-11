"""
Consistency rules between related fields.
"""
from __future__ import annotations

from typing import Dict, Iterable, List


def ensure_currency_consistency(records: Iterable[Dict[str, object]], expected: str) -> List[Dict[str, object]]:
    violations: List[Dict[str, object]] = []
    for record in records:
        currency = (record.get("currency") or "").upper()
        if currency and currency != expected.upper():
            violations.append({"record": record, "currency": currency})
    return violations

