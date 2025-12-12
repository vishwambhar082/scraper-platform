# file: src/common/db.py
"""
Shared DB helpers (connections, engines, etc.).
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Union

import psycopg2
from psycopg2.extensions import connection

from src.common.logging_utils import get_logger

log = get_logger(__name__)

_CONN: Union[connection, sqlite3.Connection, None] = None
_LOCK = threading.Lock()


def get_conn() -> Union[connection, sqlite3.Connection]:
    """Return a process-wide database connection.

    Uses PostgreSQL if DB_URL is set, otherwise falls back to SQLite
    for local/test environments.
    """

    global _CONN
    if _CONN is not None:
        return _CONN
    with _LOCK:
        if _CONN is None:
            db_url = os.getenv("DB_URL")
            if not db_url:
                # Fallback to SQLite for local/test environments
                db_path = os.getenv("RUN_DB_PATH", ":memory:")
                log.info(f"DB_URL not set, using SQLite database: {db_path}")
                _CONN = sqlite3.connect(db_path, check_same_thread=False)
            else:
                _CONN = psycopg2.connect(db_url)
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


def is_sqlite() -> bool:
    """Check if current connection is SQLite."""
    conn = get_conn()
    return isinstance(conn, sqlite3.Connection)


def cursor_wrapper(conn, **kwargs):
    """
    Create a cursor with proper context manager support for both PostgreSQL and SQLite.

    PostgreSQL cursors support context managers natively.
    SQLite cursors do not, so we wrap them.
    """
    if isinstance(conn, sqlite3.Connection):
        # SQLite - return a simple cursor (no context manager support needed for SQLite)
        # The caller should just use cursor.execute() and cursor.fetchall()
        return conn.cursor()
    else:
        # PostgreSQL - use cursor_factory if provided
        return conn.cursor(**kwargs)


__all__ = ["get_conn", "transaction", "is_sqlite", "cursor_wrapper"]
