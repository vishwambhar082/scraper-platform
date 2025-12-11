# file: src/common/db.py
"""
Shared DB helpers (connections, engines, etc.).
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection

_CONN: connection | None = None
_LOCK = threading.Lock()


def get_conn() -> connection:
    """Return a process-wide psycopg2 connection using ``DB_URL``."""

    global _CONN
    if _CONN is not None:
        return _CONN
    with _LOCK:
        if _CONN is None:
            _CONN = psycopg2.connect(os.getenv("DB_URL"))
        return _CONN


@contextmanager
def transaction():
    """Context manager that wraps a database transaction."""

    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


__all__ = ["get_conn", "transaction"]
