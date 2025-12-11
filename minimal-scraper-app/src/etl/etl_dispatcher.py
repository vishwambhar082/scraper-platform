# src/etl/etl_dispatcher.py
from __future__ import annotations

from typing import Any, Dict, Iterable

from src.common.logging_utils import get_logger
from src.etl.bigquery_loader import load_to_bigquery
from src.etl.snowflake_loader import load_to_snowflake
from src.etl.kafka_producer import publish_records

log = get_logger("etl-dispatcher")


def dispatch_etl(
    backend: str,
    target: str,
    records: Iterable[Dict[str, Any]],
    dry_run: bool = False,
) -> int:
    backend = backend.lower()
    if backend == "bigquery":
        return load_to_bigquery(target, records, dry_run=dry_run)
    if backend == "snowflake":
        return load_to_snowflake(target, records, dry_run=dry_run)
    if backend == "kafka":
        return publish_records(target, records, dry_run=dry_run)
    raise ValueError(f"Unknown ETL backend: {backend!r}")
