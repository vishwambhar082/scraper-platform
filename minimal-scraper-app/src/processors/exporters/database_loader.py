# file: src/processors/exporters/database_loader.py
"""
Database export helper.

This implementation writes records to Postgres using psycopg2.

It expects either:
- DB_DSN                          (full DSN string), OR
- DB_NAME, DB_USER, DB_PASS,
  DB_HOST, DB_PORT                (to build a DSN), AND
- DB_TABLE or SCRAPER_DB_TABLE    (target table name)

If these are not set, it will raise RuntimeError instead of silently
doing nothing.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Mapping, Any, List

from src.common.logging_utils import get_logger

log = get_logger("database-loader")

try:
    import psycopg2
except Exception:  # pragma: no cover - import guard
    psycopg2 = None  # type: ignore[attr-defined]

_TABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$")


def _get_dsn() -> str:
    dsn = os.getenv("DB_DSN")
    if dsn:
        return dsn

    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")

    if not (name and user and password):
        raise RuntimeError(
            "Database export requested but DB_DSN or "
            "(DB_NAME, DB_USER, DB_PASS) are not set"
        )

    return (
        f"dbname={name} user={user} password={password} "
        f"host={host} port={port}"
    )


def _get_table_name(explicit: str | None = None) -> str:
    table = explicit or os.getenv("DB_TABLE") or os.getenv("SCRAPER_DB_TABLE")
    if not table:
        raise RuntimeError(
            "Database export requested but DB_TABLE or SCRAPER_DB_TABLE "
            "env var is not set"
        )
    if not _TABLE_NAME_RE.match(table):
        raise RuntimeError(f"Unsafe table name for export: {table!r}")
    return table


def export_records(
    records: Iterable[Mapping[str, Any]],
    table: str | None = None,
) -> int:
    """
    Persist records into the warehouse / OLTP DB.

    Args:
        records: iterable of dict-like rows.
        table: optional table name override. If not provided, will use
               DB_TABLE or SCRAPER_DB_TABLE env var.

    Returns:
        Number of rows successfully inserted.

    Raises:
        RuntimeError if psycopg2 or DB configuration is missing.
    """
    recs: List[Mapping[str, Any]] = list(records)
    if not recs:
        log.info("database_loader: no records to export")
        return 0

    if psycopg2 is None:  # type: ignore[truthy-function]
        raise RuntimeError(
            "Database export requested but psycopg2 is not available. "
            "Install psycopg2 or vendor it into the runtime."
        )

    table_name = _get_table_name(table)
    dsn = _get_dsn()

    # Union of keys across all records
    cols = sorted({k for r in recs for k in r.keys()})
    if not cols:
        log.warning("database_loader: records have no columns; skipping export")
        return 0

    log.info(
        "database_loader: exporting %d records to %s",
        len(recs),
        table_name,
    )

    # Bulk insert using executemany (avoids psycopg2.extras dependency)
    # This works on Windows and is more portable
    with psycopg2.connect(dsn) as conn:  # type: ignore[call-arg]
        with conn.cursor() as cur:
            # Build safe column names (already validated by _get_table_name)
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(["%s"] * len(cols))
            insert_sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})'

            # Batch insert in chunks of 1000 for efficiency
            batch_size = 1000
            inserted = 0
            for i in range(0, len(recs), batch_size):
                batch = recs[i : i + batch_size]
                batch_rows = [tuple(r.get(c) for c in cols) for r in batch]
                cur.executemany(insert_sql, batch_rows)
                inserted += len(batch_rows)

            conn.commit()

    log.info(
        "database_loader: successfully exported %d records to %s",
        inserted,
        table_name,
    )
    return inserted
