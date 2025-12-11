from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from src.common.logging_utils import get_logger

log = get_logger("etl-bigquery")

try:
    from google.cloud import bigquery  # type: ignore[import]
except Exception:  # pragma: no cover
    bigquery = None  # type: ignore[assignment]


def load_to_bigquery(
    table_id: str,
    rows: Iterable[Dict[str, Any]],
    dry_run: bool = False,
) -> int:
    """
    Load rows into BigQuery table.

    Requires:
      - GOOGLE_APPLICATION_CREDENTIALS env var
      - google-cloud-bigquery installed

    If dependencies are missing, raises RuntimeError to avoid fake success.
    """
    try:
        rows_list: List[Dict[str, Any]] = list(rows)
    except Exception as exc:
        log.error("Failed to materialize rows for BigQuery load", extra={"error": str(exc)})
        return 0
    if not rows_list:
        return 0

    if dry_run:
        log.info("BigQuery dry-run: table=%s, rows=%d", table_id, len(rows_list))
        return len(rows_list)

    if bigquery is None:
        raise RuntimeError("google-cloud-bigquery not installed")

    client = bigquery.Client()
    errors = client.insert_rows_json(table_id, rows_list)
    if errors:
        log.error("BigQuery load errors", extra={"errors": errors})
        raise RuntimeError(f"BigQuery insert_rows_json failed: {errors}")

    log.info("Loaded rows into BigQuery", extra={"table_id": table_id, "rows": len(rows_list)})
    return len(rows_list)
