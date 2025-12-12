# src/agents/selector_patch_applier.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.agents.deepagent_selector_healer import SelectorPatch
from src.common.logging_utils import get_logger

log = get_logger("selector-patch-applier")


def load_selectors(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"selectors.json not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_selectors(path: Path, selectors: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(selectors, indent=2, sort_keys=True), encoding="utf-8")


def apply_patches(selectors: Dict[str, Any], patches: List[SelectorPatch]) -> Dict[str, Any]:
    for p in patches:
        field_data = selectors.get(p.field) or {}
        old = field_data.get("css") or field_data.get("xpath")
        if "css" in field_data:
            field_data["css"] = p.new_selector
        elif "xpath" in field_data:
            field_data["xpath"] = p.new_selector
        else:
            field_data["css"] = p.new_selector
        selectors[p.field] = field_data
        log.info(
            "Applied selector patch for %s: %r -> %r (conf=%.2f)",
            p.field,
            old,
            p.new_selector,
            p.confidence,
        )
    return selectors
