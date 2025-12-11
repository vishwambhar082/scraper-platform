"""
Change log repository for schema drift notifications.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List


class ChangeLogRepository:
    def __init__(self) -> None:
        self._log: List[Dict[str, object]] = []

    def record(self, source: str, description: str) -> None:
        self._log.append(
            {
                "source": source,
                "description": description,
                "recorded_at": datetime.utcnow().isoformat(),
            }
        )

    def list_entries(self, limit: int = 50) -> List[Dict[str, object]]:
        return self._log[-limit:]

