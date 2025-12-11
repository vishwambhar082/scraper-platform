# file: src/processors/parse/parse_html.py
"""
Generic HTML parsing helpers used by multiple scrapers.
"""

from __future__ import annotations

from typing import Any, Dict

from bs4 import BeautifulSoup  # ensure this is in requirements.txt


def parse_html(html: str) -> Dict[str, Any]:
    """
    Very small convenience wrapper that returns a BeautifulSoup-based parse tree
    as a dict-like structure. Real implementations will likely be source-specific.
    """
    soup = BeautifulSoup(html, "html.parser")
    return {"soup": soup}
