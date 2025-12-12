"""
API routes for log streaming and querying.

Provides access to scraper execution logs.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from psycopg2.extras import RealDictCursor

from src.common import db
from src.common.logging_utils import get_logger
from src.common.paths import LOGS_DIR

log = get_logger("logs-api")

router = APIRouter(prefix="/api/logs", tags=["logs"])

LOG_FILE = LOGS_DIR / "scraper-platform.jsonl"


def _ensure_log_table() -> bool:
    global _LOG_SCHEMA_INITIALIZED
    if _LOG_SCHEMA_INITIALIZED:
        return True
    try:
        with db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS scraper")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {LOG_TABLE} (
                        id BIGSERIAL PRIMARY KEY,
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
                        level TEXT,
                        source TEXT,
                        run_id TEXT,
                        step TEXT,
                        message TEXT NOT NULL,
                        payload JSONB
                    )
                    """
                )
        _LOG_SCHEMA_INITIALIZED = True
        return True
    except Exception as exc:  # pragma: no cover - defensive
        log.debug("Log schema init failed", extra={"error": str(exc)})
        return False


LOG_TABLE = "scraper.execution_logs"
_LOG_SCHEMA_INITIALIZED = False


def _build_filters(
    *,
    source: Optional[str],
    run_id: Optional[str],
    level: Optional[str],
) -> Tuple[List[str], List[Any]]:
    clauses = ["1=1"]
    params: List[Any] = []
    if source:
        clauses.append("source = %s")
        params.append(source)
    if run_id:
        clauses.append("run_id = %s")
        params.append(run_id)
    if level:
        clauses.append("LOWER(level) = LOWER(%s)")
        params.append(level)
    return clauses, params


def _matches_filters(entry: Dict[str, Any], source: Optional[str], run_id: Optional[str], level: Optional[str]) -> bool:
    if source and entry.get("source") != source:
        return False
    if run_id and entry.get("run_id") != run_id:
        return False
    if level and entry.get("level", "").lower() != level.lower():
        return False
    return True


def _serialize_db_log(row: Dict[str, Any]) -> Dict[str, Any]:
    payload = row.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"raw": payload}
    timestamp = row.get("timestamp")
    return {
        "id": row.get("id"),
        "timestamp": timestamp.isoformat() if timestamp else None,
        "level": row.get("level"),
        "source": row.get("source"),
        "run_id": row.get("run_id"),
        "step": row.get("step"),
        "message": row.get("message"),
        "payload": payload or {},
    }


def _query_logs_from_db(
    *,
    source: Optional[str],
    run_id: Optional[str],
    level: Optional[str],
    limit: int,
    offset: int,
) -> Optional[Dict[str, Any]]:
    if not _ensure_log_table():
        return None

    clauses, params = _build_filters(source=source, run_id=run_id, level=level)
    where_clause = " AND ".join(clauses)

    try:
        with db.transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, timestamp, level, source, run_id, step, message, payload
                    FROM {LOG_TABLE}
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                    """,
                    (*params, limit, offset),
                )
                rows = cur.fetchall()

                cur.execute(
                    f"SELECT COUNT(*) AS total FROM {LOG_TABLE} WHERE {where_clause}",
                    params,
                )
                total = cur.fetchone()["total"]
    except Exception as exc:  # pragma: no cover - defensive
        log.debug("Log DB query failed", extra={"error": str(exc)})
        return None

    return {
        "logs": [_serialize_db_log(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _read_logs_from_file(
    *,
    source: Optional[str],
    run_id: Optional[str],
    level: Optional[str],
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    if not LOG_FILE.exists():
        return {"logs": [], "total": 0, "limit": limit, "offset": offset}

    entries: List[Dict[str, Any]] = []
    try:
        with LOG_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                if not _matches_filters(entry, source, run_id, level):
                    continue
                entries.append(entry)
    except FileNotFoundError:
        entries = []

    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    total = len(entries)
    page = entries[offset : offset + limit]
    return {"logs": page, "total": total, "limit": limit, "offset": offset}


def _read_logs(
    *,
    source: Optional[str],
    run_id: Optional[str],
    level: Optional[str],
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    db_payload = _query_logs_from_db(source=source, run_id=run_id, level=level, limit=limit, offset=offset)
    if db_payload is not None:
        return db_payload
    return _read_logs_from_file(source=source, run_id=run_id, level=level, limit=limit, offset=offset)


def _poll_db_logs_since(
    last_id: int,
    *,
    source: Optional[str],
    run_id: Optional[str],
    level: Optional[str],
    batch_size: int = 200,
) -> Optional[List[Dict[str, Any]]]:
    if not _ensure_log_table():
        return None
    clauses, params = _build_filters(source=source, run_id=run_id, level=level)
    clauses.append("id > %s")
    params.append(last_id)
    where_clause = " AND ".join(clauses)

    try:
        with db.transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, timestamp, level, source, run_id, step, message, payload
                    FROM {LOG_TABLE}
                    WHERE {where_clause}
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (*params, batch_size),
                )
                rows = cur.fetchall()
    except Exception as exc:  # pragma: no cover - defensive
        log.debug("Log DB stream poll failed", extra={"error": str(exc)})
        return None

    return [_serialize_db_log(row) for row in rows]


def _latest_log_id(source: Optional[str], run_id: Optional[str], level: Optional[str]) -> int:
    if not _ensure_log_table():
        return 0
    clauses, params = _build_filters(source=source, run_id=run_id, level=level)
    where_clause = " AND ".join(clauses)
    try:
        with db.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {LOG_TABLE} WHERE {where_clause}", params)
                value = cur.fetchone()[0]
                return int(value or 0)
    except Exception as exc:  # pragma: no cover - defensive
        log.debug("Latest log id query failed", extra={"error": str(exc)})
        return 0


def _read_file_stream_chunk(
    position: int,
    *,
    source: Optional[str],
    run_id: Optional[str],
    level: Optional[str],
) -> Tuple[int, List[Dict[str, Any]]]:
    entries: List[Dict[str, Any]] = []
    if LOG_FILE.exists():
        current_size = LOG_FILE.stat().st_size
        if current_size < position:
            position = 0
        with LOG_FILE.open("r", encoding="utf-8") as handle:
            handle.seek(position)
            for line in handle:
                position = handle.tell()
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                if not _matches_filters(entry, source, run_id, level):
                    continue
                entries.append(entry)
    return position, entries


@router.get("")
def get_logs(
    source: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    return _read_logs(source=source, run_id=run_id, level=level, limit=limit, offset=offset)


def _format_sse(payload: Dict[str, Any]) -> str:
    return f"event: log\ndata: {json.dumps(payload)}\n\n"


async def _log_stream(
    *,
    request: Request,
    source: Optional[str],
    run_id: Optional[str],
    level: Optional[str],
    poll_interval: float = 1.0,
) -> Any:
    position = 0
    use_db_stream = _ensure_log_table()
    last_id = _latest_log_id(source, run_id, level) if use_db_stream else 0

    while True:
        if await request.is_disconnected():
            break

        if use_db_stream:
            rows = _poll_db_logs_since(last_id, source=source, run_id=run_id, level=level)
            if rows is None:
                use_db_stream = False
            else:
                for row in rows:
                    last_id = max(last_id, int(row.get("id") or last_id))
                    yield _format_sse(row)

        if not use_db_stream:
            position, entries = _read_file_stream_chunk(position, source=source, run_id=run_id, level=level)
            for entry in entries:
                yield _format_sse(entry)

        await asyncio.sleep(poll_interval)


@router.get("/stream")
def stream_logs(
    request: Request,
    source: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
) -> StreamingResponse:
    """
    Server-Sent Events stream of log entries filtered by optional criteria.
    """
    generator = _log_stream(request=request, source=source, run_id=run_id, level=level)
    return StreamingResponse(generator, media_type="text/event-stream")
