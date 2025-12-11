# file: src/common/file_store.py
"""
Abstraction for file storage (local, S3, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Union


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists and return its Path.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
