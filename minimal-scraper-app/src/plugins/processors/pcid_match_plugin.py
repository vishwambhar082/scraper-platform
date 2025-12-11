# file: src/plugins/processors/pcid_match_plugin.py
"""
Plugin wrapper around the PCID matching utilities.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.processors.pcid import pcid_matching


def match_pcids(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return a list of candidate PCID matches for a given normalized record.
    """
    return pcid_matching.match_pcids(record)
