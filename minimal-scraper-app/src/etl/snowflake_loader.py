from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from src.common.logging_utils import get_logger

log = get_logger("etl-snowflake")

try:
    import snowflake.connector  # type: ignore[import]
except Exception:  # pragma: no cover
    snowflake = None  # type: ignore[assignment]
else:
    snowflake = snowflake.connector  # type: ignore[assignment]


def load_to_snowflake(
    table: str,
    rows: Iterable[Dict[str, Any]],
    dry_run: bool = False,
) -> int:
    """
    Load rows into Snowflake table using simple INSERTs.

    Requires:
      - SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE,
        SNOWFLAKE_SCHEMA, SNOWFLAKE_WAREHOUSE env vars.
      - snowflake-connector-python installed.
    """
    try:
        rows_list: List[Dict[str, Any]] = list(rows)
    except Exception as exc:
        log.error("Failed to materialize rows for Snowflake load", extra={"error": str(exc)})
        return 0
    if not rows_list:
        return 0

    if dry_run:
        log.info("Snowflake dry-run: table=%s, rows=%d", table, len(rows_list))
        return len(rows_list)

    cfg = {
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    }
    if not all(cfg.values()):
        raise RuntimeError("Snowflake env vars not fully configured")

    if snowflake is None:
        raise RuntimeError("snowflake-connector-python not installed")

    cols = sorted({k for r in rows_list for k in r.keys()})
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)

    conn = snowflake.connect(**cfg)  # type: ignore[call-arg]
    try:
        with conn.cursor() as cur:
            for r in rows_list:
                cur.execute(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                    [r.get(c) for c in cols],
                )
        conn.commit()
    finally:
        conn.close()

    log.info("Loaded rows into Snowflake", extra={"table": table, "rows": len(rows_list)})
    return len(rows_list)
