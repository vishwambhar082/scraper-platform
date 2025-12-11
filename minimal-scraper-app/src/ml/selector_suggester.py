"""
Suggest CSS selectors based on historical success rates.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Tuple


class SelectorSuggester:
    def __init__(self) -> None:
        self._stats: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))

    def record_result(self, selector: str, success: bool) -> None:
        success_count, total = self._stats[selector]
        self._stats[selector] = (success_count + int(success), total + 1)

    def best_selector(self) -> str | None:
        if not self._stats:
            return None
        return max(self._stats.items(), key=lambda item: (item[1][0] / item[1][1], item[1][1]))[0]

    def bulk_record(self, results: Iterable[Tuple[str, bool]]) -> None:
        for selector, success in results:
            self.record_result(selector, success)

