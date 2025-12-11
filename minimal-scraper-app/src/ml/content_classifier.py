"""
Keyword-based content classifier used for quick labeling.
"""
from __future__ import annotations

from typing import Dict


class ContentClassifier:
    def __init__(self, keyword_map: Dict[str, str] | None = None) -> None:
        self.keyword_map = keyword_map or {
            "rx": "prescription",
            "otc": "over_the_counter",
            "generic": "generic",
        }

    def classify(self, text: str) -> str:
        lowered = text.lower()
        for keyword, label in self.keyword_map.items():
            if keyword in lowered:
                return label
        return "unknown"

