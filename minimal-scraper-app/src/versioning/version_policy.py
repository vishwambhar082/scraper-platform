# src/versioning/version_policy.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class VersionPolicy:
    strategy: str = "append"
    keep_history: bool = True
    max_history_versions: Optional[int] = None
