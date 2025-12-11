from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from src.api.models import RunDetail, RunStep, RunSummary, VariantBenchmark
from src.run_tracking import query as run_query
from src.common.logging_utils import get_logger


# Basic in-memory dataset to back the dashboard APIs while a real database layer is wired.
log = get_logger("run-store")

RUN_SUMMARIES: List[RunSummary] = [
    RunSummary(
        id="run_2024_001",
        source="alfabeta",
        status="success",
        startedAt=datetime.fromisoformat("2024-05-01T10:00:00+00:00"),
        durationSeconds=120,
        variantId="v1_baseline",
    ),
    RunSummary(
        id="run_2024_002",
        source="quebec",
        status="failed",
        startedAt=datetime.fromisoformat("2024-05-01T11:00:00+00:00"),
        durationSeconds=45,
        variantId="v2_aggressive_pcids",
    ),
    RunSummary(
        id="run_2024_003",
        source="lafa",
        status="running",
        startedAt=datetime.fromisoformat("2024-05-01T11:30:00+00:00"),
        variantId="v1_baseline",
    ),
]

RUN_STEPS: Dict[str, List[RunStep]] = {
    "run_2024_001": [
        RunStep(
            id="step1",
            name="company_index",
            status="success",
            startedAt=datetime.fromisoformat("2024-05-01T10:00:00+00:00"),
            durationSeconds=30,
        ),
        RunStep(
            id="step2",
            name="product_index",
            status="success",
            startedAt=datetime.fromisoformat("2024-05-01T10:00:30+00:00"),
            durationSeconds=40,
        ),
        RunStep(
            id="step3",
            name="extract_product",
            status="success",
            startedAt=datetime.fromisoformat("2024-05-01T10:01:10+00:00"),
            durationSeconds=50,
        ),
    ],
    "run_2024_002": [
        RunStep(
            id="step1",
            name="company_index",
            status="failed",
            startedAt=datetime.fromisoformat("2024-05-01T11:00:00+00:00"),
            durationSeconds=45,
        )
    ],
    "run_2024_003": [
        RunStep(
            id="step1",
            name="company_index",
            status="success",
            startedAt=datetime.fromisoformat("2024-05-01T11:30:00+00:00"),
            durationSeconds=20,
        ),
        RunStep(
            id="step2",
            name="product_index",
            status="running",
            startedAt=datetime.fromisoformat("2024-05-01T11:30:20+00:00"),
        ),
    ],
}

RUN_DETAILS: Dict[str, RunDetail] = {
    "run_2024_001": RunDetail(
        id="run_2024_001",
        source="alfabeta",
        status="success",
        startedAt=datetime.fromisoformat("2024-05-01T10:00:00+00:00"),
        finishedAt=datetime.fromisoformat("2024-05-01T10:02:00+00:00"),
        stats={"products": 1200, "invalid": 12, "drift_events": 0},
        metadata={"version": "4.9.0", "env": "prod", "variant_id": "v1_baseline"},
    ),
    "run_2024_002": RunDetail(
        id="run_2024_002",
        source="quebec",
        status="failed",
        startedAt=datetime.fromisoformat("2024-05-01T11:00:00+00:00"),
        stats={"products": 0, "invalid": 0, "drift_events": 1},
        metadata={"error": "Drift detected on listing page", "variant_id": "v2_aggressive_pcids"},
    ),
    "run_2024_003": RunDetail(
        id="run_2024_003",
        source="lafa",
        status="running",
        startedAt=datetime.fromisoformat("2024-05-01T11:30:00+00:00"),
        stats={"products": 200},
        metadata={"note": "still running", "variant_id": "v1_baseline"},
    ),
}

VARIANT_BASELINES: List[VariantBenchmark] = [
    VariantBenchmark(
        variantId="v1_baseline",
        totalRuns=12,
        successRate=0.92,
        dataCompleteness=0.97,
        costPerRecord=0.004,
        totalRecords=3200,
    ),
    VariantBenchmark(
        variantId="v2_aggressive_pcids",
        totalRuns=8,
        successRate=0.75,
        dataCompleteness=0.83,
        costPerRecord=0.003,
        totalRecords=4100,
    ),
]


def list_runs(tenant_id: Optional[str] = None) -> List[RunSummary]:
    db_runs = _fetch_runs_from_db(limit=500, tenant_id=tenant_id)
    if db_runs:
        return db_runs

    if tenant_id and tenant_id != "default":
        return []

    return RUN_SUMMARIES


def list_runs_paginated(limit: int = 50, offset: int = 0, *, tenant_id: Optional[str] = None) -> List[RunSummary]:
    """
    Return a slice of runs for pagination.

    NOTE: currently backed by in-memory RUN_SUMMARIES; once wired to DB,
    this should become a proper SELECT ... LIMIT/OFFSET query.
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    try:
        offset = int(offset)
    except (TypeError, ValueError):
        offset = 0

    db_runs = _fetch_runs_from_db(limit=limit + offset, tenant_id=tenant_id)
    if db_runs:
        runs = db_runs
    elif tenant_id and tenant_id != "default":
        return []
    else:
        runs = RUN_SUMMARIES

    if limit <= 0:
        limit = 50
    if offset < 0:
        offset = 0

    return runs[offset : offset + limit]


def get_run_detail(run_id: str, *, tenant_id: Optional[str] = None) -> Optional[RunDetail]:
    db_detail = _fetch_run_detail_from_db(run_id, tenant_id=tenant_id)
    if db_detail:
        return db_detail

    if tenant_id and tenant_id != "default":
        return None

    detail = RUN_DETAILS.get(run_id)
    if not detail:
        return None
    steps = RUN_STEPS.get(run_id, [])
    # Return a copy so we do not mutate the global object when serializing steps.
    return RunDetail(**detail.model_dump(exclude={"steps"}), steps=steps)


def list_variant_benchmarks(source: Optional[str] = None, tenant_id: Optional[str] = None) -> List[VariantBenchmark]:
    """
    List variant benchmarks with tenant isolation.
    
    Args:
        source: Optional source filter
        tenant_id: Optional tenant_id for isolation (defaults to 'default')
    """
    effective_tenant_id = tenant_id or "default"
    rows = run_query.variant_benchmarks(source, tenant_id=effective_tenant_id)
    if rows:
        return [
            VariantBenchmark(
                variantId=row["variant_id"],
                totalRuns=row["total_runs"],
                successRate=row["success_rate"],
                dataCompleteness=row["data_completeness"],
                costPerRecord=row["cost_per_record"],
                totalRecords=row["total_records"],
            )
            for row in rows
        ]

    # Only return baselines for default tenant
    if effective_tenant_id == "default":
        return VARIANT_BASELINES
    return []


def get_run_steps(run_id: str, *, tenant_id: Optional[str] = None) -> List[RunStep]:
    db_steps = run_query.get_run_steps(run_id, tenant_id=tenant_id)
    if db_steps:
        return [
            RunStep(
                id=step["step_id"],
                name=step["name"],
                status=step["status"],
                startedAt=step["started_at"],
                durationSeconds=step["duration_seconds"],
            )
            for step in db_steps
        ]
    if tenant_id and tenant_id != "default":
        return []

    return RUN_STEPS.get(run_id, [])


def _fetch_runs_from_db(limit: int, tenant_id: Optional[str]) -> List[RunSummary]:
    try:
        rows = run_query.list_runs(limit=limit, tenant_id=tenant_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        log.debug("list_runs DB query failed", extra={"error": str(exc)})
        return []

    return [
        RunSummary(
            id=row["run_id"],
            source=row["source"],
            status=row["status"],
            startedAt=row["started_at"],
            durationSeconds=row.get("duration_seconds"),
            variantId=row.get("variant_id"),
        )
        for row in rows
    ]


def _fetch_run_detail_from_db(run_id: str, tenant_id: Optional[str]) -> Optional[RunDetail]:
    try:
        payload = run_query.get_run(run_id, tenant_id=tenant_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        log.debug("get_run DB query failed", extra={"error": str(exc), "run_id": run_id})
        return None

    if not payload:
        return None

    steps_payload = payload.get("steps") or []
    return RunDetail(
        id=payload["run_id"],
        source=payload["source"],
        status=payload["status"],
        startedAt=payload["started_at"],
        finishedAt=payload.get("finished_at"),
        durationSeconds=payload.get("duration_seconds"),
        stats=payload.get("stats") or {},
        metadata=payload.get("metadata") or {},
        variantId=(payload.get("metadata") or {}).get("variant_id"),
        steps=[
            RunStep(
                id=step["step_id"],
                name=step["name"],
                status=step["status"],
                startedAt=step["started_at"],
                durationSeconds=step.get("duration_seconds"),
            )
            for step in steps_payload
        ],
    )
