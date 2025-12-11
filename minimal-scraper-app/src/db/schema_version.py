from __future__ import annotations

import logging
from typing import Optional

from src.common.db import get_conn, transaction
from src.common.settings import get_runtime_env

log = logging.getLogger(__name__)


def _ensure_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scraper.schema_version (
            id          INTEGER PRIMARY KEY,
            version     INTEGER NOT NULL,
            updated_at  TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_schema_version_singleton
            ON scraper.schema_version (id);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_schema_version_updated_at
            ON scraper.schema_version (updated_at);
        """
    )


def schema_version_table_exists() -> bool:
    """Return ``True`` if the ``scraper.schema_version`` table exists."""

    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('scraper.schema_version');")
        return cur.fetchone()[0] is not None


def get_schema_version() -> Optional[int]:
    """
    Return the current schema version, or ``None`` if not initialized.
    """

    with transaction() as conn:
        cur = conn.cursor()
        _ensure_table(cur)
        cur.execute("SELECT version FROM scraper.schema_version WHERE id = 1;")
        row = cur.fetchone()
        if not row:
            return None
        return row[0]


def set_schema_version(version: int) -> None:
    """
    Upsert the schema version row.
    """

    with transaction() as conn:
        cur = conn.cursor()
        _ensure_table(cur)
        cur.execute(
            """
            INSERT INTO scraper.schema_version (id, version)
            VALUES (1, %s)
            ON CONFLICT (id)
            DO UPDATE SET version = EXCLUDED.version,
                          updated_at = NOW();
            """,
            (version,),
        )
    log.info(
        "Schema version updated", extra={"version": version, "env": get_runtime_env()}
    )
