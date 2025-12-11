# file: src/processors/parse/schema_drift.py
"""
Helpers to detect schema drift in parsed records.
"""

from __future__ import annotations

from typing import Dict, Set


def compute_field_diff(old: Dict[str, object], new: Dict[str, object]) -> Dict[str, Set[str]]:
    """
    Compare keys between two dicts and report added/removed fields.
    """
    old_keys = set(old.keys())
    new_keys = set(new.keys())
    return {
        "added": new_keys - old_keys,
        "removed": old_keys - new_keys,
    }
