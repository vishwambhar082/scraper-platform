from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from src.api.data.run_store import get_run_detail, list_runs_paginated
from src.api.models import RunDetail, RunSummary

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=list[RunSummary])
def get_runs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> list[RunSummary]:
    """Return a paginated list of recent scraper runs."""

    # When called directly (outside FastAPI), the defaults are Query/Header objects;
    # normalize them to plain values for compatibility with tests and scripts.
    if not isinstance(tenant_id, (str, type(None))):
        tenant_id = None

    return list_runs_paginated(limit=limit, offset=offset, tenant_id=tenant_id)


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str, tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")) -> RunDetail:
    """Return run detail for a specific run id."""

    if not isinstance(tenant_id, (str, type(None))):
        tenant_id = None

    detail = get_run_detail(run_id, tenant_id=tenant_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return detail


def _serialize_run(run: RunSummary) -> dict:
    data = run.model_dump(mode="json")
    data["startedAt"] = run.startedAt.isoformat()
    return data


def _format_sse(event: str, payload: object) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _detect_changes(
    previous_runs: dict[str, RunSummary], current_runs: dict[str, RunSummary]
) -> list[tuple[str, RunSummary | dict[str, str]]]:
    updates: list[tuple[str, RunSummary | dict[str, str]]] = []

    for run_id, run in current_runs.items():
        prev = previous_runs.get(run_id)
        if prev is None:
            updates.append(("created", run))
            continue

        if prev.status != run.status or prev.durationSeconds != run.durationSeconds:
            event = "completed" if prev.status == "running" and run.status != "running" else "updated"
            updates.append((event, run))

    for removed_id in previous_runs.keys() - current_runs.keys():
        updates.append(("deleted", {"id": removed_id}))

    return updates


async def _run_stream(
    *,
    request: Request,
    limit: int,
    offset: int,
    tenant_id: str | None,
    poll_interval_seconds: float = 2.0,
) -> AsyncIterator[str]:
    previous_runs = {
        run.id: run for run in list_runs_paginated(limit=limit, offset=offset, tenant_id=tenant_id)
    }
    yield _format_sse("snapshot", [_serialize_run(run) for run in previous_runs.values()])

    while True:
        if await request.is_disconnected():
            break

        await asyncio.sleep(poll_interval_seconds)
        current_runs = {
            run.id: run
            for run in list_runs_paginated(limit=limit, offset=offset, tenant_id=tenant_id)
        }
        changes = _detect_changes(previous_runs, current_runs)
        previous_runs = current_runs

        for event, payload in changes:
            serialized = payload if isinstance(payload, dict) else _serialize_run(payload)
            yield _format_sse(event, serialized)


@router.get("/stream")
def stream_runs(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> StreamingResponse:
    """Server-sent events stream for run updates."""

    generator = _run_stream(request=request, limit=limit, offset=offset, tenant_id=tenant_id)
    return StreamingResponse(generator, media_type="text/event-stream")
