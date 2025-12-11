# file: src/processors/parse/cleanup.py
"""
Reusable cleanup routines for raw HTML or text blobs.
"""

from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    """
    Collapse multiple spaces, strip leading/trailing whitespace.
    """
    return re.sub(r"\s+", " ", text).strip()
