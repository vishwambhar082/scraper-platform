"""
Calculate extraction confidence based on field coverage.
"""
from __future__ import annotations

from typing import Dict, Iterable


class ExtractionScorer:
    REQUIRED_FIELDS = ("pcid", "product_name", "price", "currency")

    def score(self, record: Dict[str, object]) -> float:
        covered = sum(1 for field in self.REQUIRED_FIELDS if record.get(field))
        return covered / len(self.REQUIRED_FIELDS)

    def average_score(self, records: Iterable[Dict[str, object]]) -> float:
        records = list(records)
        if not records:
            return 0.0
        total = sum(self.score(record) for record in records)
        return total / len(records)

