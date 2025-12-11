from __future__ import annotations

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PCIDMatcher:
    """Simple PCID matcher using exact field comparisons."""

    def __init__(self, master_records: List[Dict[str, Any]]) -> None:
        self.master_records = master_records

    def match_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        name = (record.get("product_name") or "").strip().lower()
        strength = (record.get("strength") or "").strip().lower()
        pack = (record.get("pack_size") or "").strip().lower()
        for m in self.master_records:
            if (
                (m.get("product_name") or "").strip().lower() == name
                and (m.get("strength") or "").strip().lower() == strength
                and (m.get("pack_size") or "").strip().lower() == pack
            ):
                return {
                    "pcid": m.get("pcid"),
                    "confidence": 1.0,
                    "match_strategy": "exact",
                }
        return {"pcid": None, "confidence": 0.0, "match_strategy": "none"}

    def match_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.match_record(r) for r in records]


__all__ = ["PCIDMatcher"]
