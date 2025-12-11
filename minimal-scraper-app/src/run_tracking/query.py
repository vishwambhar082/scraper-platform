# file: src/run_tracking/query.py
"""
Read helpers for run / step history.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.observability.cost_tracking import iter_cost_records_from_db
from src.run_tracking.db_session import get_session
from src.scheduler import scheduler_db_adapter as db


def get_run(run_id: str, *, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch a single run record by ID."""

    detail = db.fetch_run_detail(run_id, tenant_id=tenant_id) if tenant_id is not None else db.fetch_run_detail(run_id)
    if not detail:
        return None
    return {
        "run_id": detail.run_id,
        "source": detail.source,
        "status": detail.status,
        "started_at": detail.started_at,
        "finished_at": detail.finished_at,
        "duration_seconds": detail.duration_seconds,
        "stats": detail.stats,
        "metadata": detail.metadata,
        "variant_id": (detail.metadata or {}).get("variant_id"),
        "steps": [
            {
                "step_id": step.step_id,
                "name": step.name,
                "status": step.status,
                "started_at": step.started_at,
                "duration_seconds": step.duration_seconds,
            }
            for step in (db.fetch_run_steps(run_id, tenant_id=tenant_id) if tenant_id is not None else db.fetch_run_steps(run_id))
        ],
    }


def list_runs(
    source_name: Optional[str] = None,
    limit: int = 100,
    *,
    tenant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List recent runs, optionally filtered by source name."""

    runs = db.fetch_run_summaries(tenant_id=tenant_id)
    if source_name:
        runs = [r for r in runs if r.source == source_name]
    return [
        {
            "run_id": r.run_id,
            "source": r.source,
            "status": r.status,
            "started_at": r.started_at,
            "duration_seconds": r.duration_seconds,
            "variant_id": (r.metadata or {}).get("variant_id") if getattr(r, "metadata", None) else None,
        }
        for r in runs[:limit]
    ]


def persist_run_and_steps(run_payload: Dict[str, Any], steps: List[Dict[str, Any]]) -> None:
    """Write run + step records atomically to avoid partial history."""

    with get_session() as session:
        tenant_id = run_payload.get("tenant_id")
        db.upsert_run(
            run_id=run_payload["run_id"],
            source=run_payload["source"],
            status=run_payload.get("status", "pending"),
            started_at=run_payload["started_at"],
            finished_at=run_payload.get("finished_at"),
            duration_seconds=run_payload.get("duration_seconds"),
            stats=run_payload.get("stats"),
            metadata=run_payload.get("metadata"),
            tenant_id=tenant_id,
            conn=session.conn,
        )

        for step in steps:
            db.record_run_step(
                step_id=step["step_id"],
                run_id=step["run_id"],
                name=step["name"],
                status=step["status"],
                started_at=step["started_at"],
                duration_seconds=step.get("duration_seconds"),
                tenant_id=step.get("tenant_id", tenant_id),
                conn=session.conn,
            )


def get_run_steps(run_id: str, *, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return structured run steps for downstream APIs."""

    steps = db.fetch_run_steps(run_id, tenant_id=tenant_id) if tenant_id is not None else db.fetch_run_steps(run_id)
    return [
        {
            "step_id": step.step_id,
            "name": step.name,
            "status": step.status,
            "started_at": step.started_at,
            "duration_seconds": step.duration_seconds,
        }
        for step in steps
    ]


def _extract_record_counts(stats: Optional[Dict[str, Any]]) -> tuple[int, int]:
    if not stats:
        return 0, 0
    records = stats.get("records") or stats.get("products") or 0
    invalid = stats.get("invalid") or stats.get("invalid_records") or 0
    try:
        records_int = int(records)
    except (TypeError, ValueError):  # pragma: no cover - defensive casting
        records_int = 0
    try:
        invalid_int = int(invalid)
    except (TypeError, ValueError):  # pragma: no cover - defensive casting
        invalid_int = 0
    return records_int, invalid_int


def variant_benchmarks(source_name: Optional[str] = None, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get variant benchmarks with tenant isolation.
    
    Args:
        source_name: Optional source filter
        tenant_id: Optional tenant_id for isolation
    """
    effective_tenant_id = tenant_id or "default"
    runs = db.fetch_runs_with_stats(source_name, tenant_id=effective_tenant_id)
    if not runs:
        return []

    # Filter costs by tenant
    cost_index = {}
    for row in iter_cost_records_from_db():
        row_tenant = row.get("tenant_id", "default")
        if row_tenant == effective_tenant_id:
            cost_index[row.get("run_id")] = float(row.get("total_usd") or 0.0)
    aggregates: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "successes": 0, "records": 0, "invalid": 0, "cost": 0.0}
    )

    for run in runs:
        variant_id = (run.metadata or {}).get("variant_id") or "baseline"
        agg = aggregates[variant_id]
        agg["runs"] += 1
        if run.status == "success":
            agg["successes"] += 1
        records, invalid = _extract_record_counts(run.stats or {})
        agg["records"] += records
        agg["invalid"] += invalid
        agg["cost"] += cost_index.get(run.run_id, 0.0)

    benchmarks: List[Dict[str, Any]] = []
    for variant_id, stats in aggregates.items():
        total_runs = stats["runs"]
        total_records = stats["records"]
        invalid_records = stats["invalid"]
        success_rate = stats["successes"] / total_runs if total_runs else 0.0
        completeness_denom = total_records + invalid_records
        data_completeness = total_records / completeness_denom if completeness_denom else 0.0
        cost_per_record = stats["cost"] / total_records if total_records else 0.0

        benchmarks.append(
            {
                "variant_id": variant_id,
                "total_runs": total_runs,
                "success_rate": success_rate,
                "data_completeness": data_completeness,
                "cost_per_record": cost_per_record,
                "total_records": total_records,
            }
        )

    benchmarks.sort(key=lambda item: item["variant_id"])
    return benchmarks
