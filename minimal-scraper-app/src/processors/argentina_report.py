# src/processors/argentina_report.py

from collections import Counter
from typing import Dict, Iterable, Any


def build_argentina_report(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a simple aggregated report over normalized Argentina records.

    This is intentionally minimal; extend with whatever metrics you need.
    """
    records = list(records)
    total = len(records)
    by_currency = Counter(r.get("currency") for r in records)
    by_company = Counter(r.get("company") for r in records)

    return {
        "total_records": total,
        "by_currency": dict(by_currency),
        "top_companies": by_company.most_common(20),
    }
