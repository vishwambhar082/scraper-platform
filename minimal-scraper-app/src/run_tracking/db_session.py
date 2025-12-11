# file: src/run_tracking/db_session.py
"""
Thin abstraction over the DB connection used for run tracking.

Right now this is intentionally minimal – you can later swap
in SQLAlchemy or any other proper ORM / driver.
"""

from __future__ import annotations

from typing import Any, ContextManager

from src.scheduler import scheduler_db_adapter as db


class TrackingDBSession(ContextManager["TrackingDBSession"]):
    """Transactional wrapper around the scheduler DB adapter."""

    def __init__(self) -> None:
        self._tx: ContextManager | None = None
        self.conn: Any = None

    def __enter__(self) -> "TrackingDBSession":
        self._tx = db.transaction()
        self.conn = self._tx.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        assert self._tx is not None
        return self._tx.__exit__(exc_type, exc, tb)

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self.conn.execute(*args, **kwargs)


def get_session() -> TrackingDBSession:
    """Obtain a transactional session for run tracking writes."""

    return TrackingDBSession()
