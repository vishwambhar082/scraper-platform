from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response
from openpyxl import Workbook
from psycopg2.extras import RealDictCursor

from src.common import db
from src.common.logging_utils import get_logger

log = get_logger("audit-api")

router = APIRouter(prefix="/api/audit", tags=["audit"])

MAX_EXPORT_ROWS = 50000


def _build_filters(
    *,
    event_type: Optional[str],
    source: Optional[str],
    run_id: Optional[str],
) -> Tuple[str, List[Any]]:
    clauses = ["1=1"]
    params: List[Any] = []
    if event_type:
        clauses.append("event_type = %s")
        params.append(event_type)
    if source:
        clauses.append("source = %s")
        params.append(source)
    if run_id:
        clauses.append("run_id = %s")
        params.append(run_id)
    return " AND ".join(clauses), params


def _serialize_event(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row["id"]),
        "event_type": row["event_type"],
        "source": row.get("source"),
        "run_id": row.get("run_id"),
        "payload": row.get("payload") or {},
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def _build_filename(prefix: str, extension: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def _validate_format(export_format: str) -> str:
    normalized = export_format.lower()
    if normalized not in {"csv", "xlsx", "json"}:
        raise HTTPException(status_code=400, detail="Invalid export format. Use csv, xlsx, or json.")
    return normalized


def _enforce_export_limits(total: int) -> None:
    if total > MAX_EXPORT_ROWS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Export too large ({total} rows). Please narrow your filters below {MAX_EXPORT_ROWS} rows "
                "or export a smaller time range."
            ),
        )


@router.get("/events")
def get_audit_events(
    event_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
) -> dict:
    """
    Fetch audit trail events from Postgres.
    
    Tenant isolation: If tenant_id is provided, only returns events for that tenant.
    If not provided, returns events for 'default' tenant.
    """
    # Enforce tenant isolation - default to 'default' if not provided
    effective_tenant_id = tenant_id or "default"
    
    where_clause, params = _build_filters(event_type=event_type, source=source, run_id=run_id)
    
    # Add tenant_id filter
    where_clause = f"{where_clause} AND tenant_id = %s"
    params.append(effective_tenant_id)

    with db.transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, event_type, source, run_id, payload, created_at
                FROM scraper.audit_events
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (*params, limit, offset),
            )
            rows = cur.fetchall()

            cur.execute(
                f"SELECT COUNT(*) AS total FROM scraper.audit_events WHERE {where_clause}",
                params,
            )
            total = cur.fetchone()["total"]

    return {
        "events": [_serialize_event(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "tenant_id": effective_tenant_id,
    }


@router.get("/export")
def export_audit_events(
    export_format: str = Query("csv", alias="format"),
    event_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
) -> Response:
    """Export all audit events that match the provided filters.

    - Respects tenant isolation via X-Tenant-Id.
    - Applies the same filters as the list endpoint but without pagination.
    - Supports csv, xlsx, and json output formats.
    """

    normalized_format = _validate_format(export_format)
    effective_tenant_id = tenant_id or "default"

    where_clause, params = _build_filters(event_type=event_type, source=source, run_id=run_id)
    where_clause = f"{where_clause} AND tenant_id = %s"
    params.append(effective_tenant_id)

    with db.transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"SELECT COUNT(*) AS total FROM scraper.audit_events WHERE {where_clause}", params
            )
            total = cur.fetchone()["total"]
            _enforce_export_limits(total)

            cur.execute(
                f"""
                SELECT id, event_type, source, run_id, payload, created_at
                FROM scraper.audit_events
                WHERE {where_clause}
                ORDER BY created_at DESC
                """,
                params,
            )
            rows = cur.fetchall()

    events = [_serialize_event(row) for row in rows]
    filename = _build_filename("audit_events", normalized_format)
    headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}

    if normalized_format == "json":
        return Response(
            json.dumps(events, ensure_ascii=False, default=str),
            media_type="application/json",
            headers=headers,
        )

    if normalized_format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "event_type", "source", "run_id", "created_at", "payload"])
        for event in events:
            writer.writerow(
                [
                    event.get("id"),
                    event.get("event_type"),
                    event.get("source"),
                    event.get("run_id"),
                    event.get("created_at"),
                    json.dumps(event.get("payload") or {}),
                ]
            )

        return Response(
            buffer.getvalue().encode("utf-8"),
            media_type="text/csv",
            headers=headers,
        )

    # xlsx export
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Audit Events"
    sheet.append(["id", "event_type", "source", "run_id", "created_at", "payload"])
    for event in events:
        sheet.append(
            [
                event.get("id"),
                event.get("event_type"),
                event.get("source"),
                event.get("run_id"),
                event.get("created_at"),
                json.dumps(event.get("payload") or {}),
            ]
        )

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return Response(
        output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )

