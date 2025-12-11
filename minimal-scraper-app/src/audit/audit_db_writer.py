from __future__ import annotations

import json
from typing import Any, Dict

from src.common.logging_utils import get_logger
from src.processors.exporters.database_loader import _get_dsn  # reuse DSN helper

log = get_logger("audit-db-writer")

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[attr-defined]


def write_audit_event_to_db(payload: Dict[str, Any]) -> None:
    """
    Persist an audit event to the DB.

    Expected table (add via migration):

        CREATE TABLE IF NOT EXISTS scraper.audit_events (
            id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type  text NOT NULL,
            source      text,
            run_id      text,
            payload     jsonb NOT NULL,
            created_at  timestamptz NOT NULL DEFAULT now()
        );

    This function is best-effort: it logs on failure rather than raising.
    """
    if not payload:
        return

    if psycopg2 is None:  # type: ignore[truthy-function]
        log.warning(
            "Audit event dropped because psycopg2 is not available",
            extra={"payload_keys": list(payload.keys())},
        )
        return

    event_type = str(payload.get("event_type") or "generic")
    source = str(payload.get("source") or "")
    run_id = str(payload.get("run_id") or "")
    tenant_id = str(payload.get("tenant_id") or "default")

    try:
        dsn = _get_dsn()
        with psycopg2.connect(dsn) as conn:  # type: ignore[call-arg]
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scraper.audit_events
                        (event_type, source, run_id, tenant_id, payload)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        event_type,
                        source,
                        run_id,
                        tenant_id,
                        json.dumps(payload, default=str),
                    ),
                )
        log.info(
            "Audit event written",
            extra={"event_type": event_type, "source": source, "run_id": run_id},
        )
    except Exception as exc:  # pragma: no cover
        log.error(
            "Failed to write audit event",
            extra={
                "error": str(exc),
                "event_type": event_type,
                "source": source,
                "run_id": run_id,
            },
        )
