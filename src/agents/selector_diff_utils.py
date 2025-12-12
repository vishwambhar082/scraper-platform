# src/agents/selector_diff_utils.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SelectorDiff:
    field: str
    old: Any
    new: Any


def diff_selectors(old: Dict[str, Any], new: Dict[str, Any]) -> List[SelectorDiff]:
    diffs: List[SelectorDiff] = []
    all_keys = set(old.keys()) | set(new.keys())
    for k in sorted(all_keys):
        ov = old.get(k)
        nv = new.get(k)
        if ov != nv:
            diffs.append(SelectorDiff(field=k, old=ov, new=nv))
    return diffs
