"""
Repository abstraction over run_tracking storage.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from src.run_tracking.recorder import RunRecorder


class RunsRepository:
    def __init__(self) -> None:
        self._recorder = RunRecorder()

    def list_recent(self, source: Optional[str] = None, limit: int = 20) -> List[Dict[str, object]]:
        return self._recorder.list_recent(source=source, limit=limit)

    def get(self, run_id: str) -> Optional[Dict[str, object]]:
        return self._recorder.get_run(run_id)

