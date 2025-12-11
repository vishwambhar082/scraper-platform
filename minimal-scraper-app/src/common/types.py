"""
Shared type aliases/dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class RunMetadata:
    run_id: str
    source: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    extra: Dict[str, object]

