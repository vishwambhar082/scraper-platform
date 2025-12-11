from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Header

from src.api.models import SourceHealth
from src.db.schema_version import get_schema_version
from src.scheduler.scheduler_db_adapter import fetch_source_metrics

router = APIRouter(prefix="/api/source-health", tags=["source-health"])


@router.get("", response_model=List[SourceHealth])
def get_source_health(
    tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> List[SourceHealth]:
    """Return health metrics for each scraper source.

    Tenant isolation: If tenant_id is provided, only returns metrics for that tenant.
    If not provided, returns metrics for 'default' tenant.
    
    Falls back to a small in-memory dataset if the scheduler DB adapter does not
    yet provide real data.
    """
    # Enforce tenant isolation - default to 'default' if not provided
    effective_tenant_id = tenant_id or "default"

    metrics = fetch_source_metrics(tenant_id=effective_tenant_id)
    if metrics:
        return [
            SourceHealth(
                source=row.source,
                status="healthy" if row.consecutive_failures == 0 else "degraded",
                lastRunAt=row.last_run_at,
                lastSuccessAt=row.last_success_at,
                consecutiveFailures=row.consecutive_failures,
                budgetExhausted=row.budget_exhausted,
            )
            for row in metrics
        ]

    # Safe fallback until DB wiring is complete
    return [
        SourceHealth(
            source="alfabeta",
            status="healthy",
            lastRunAt=datetime.fromisoformat("2024-05-01T10:02:00+00:00"),
            lastSuccessAt=datetime.fromisoformat("2024-05-01T10:02:00+00:00"),
            consecutiveFailures=0,
            budgetExhausted=False,
        ),
        SourceHealth(
            source="quebec",
            status="degraded",
            lastRunAt=datetime.fromisoformat("2024-05-01T11:00:00+00:00"),
            lastSuccessAt=None,
            consecutiveFailures=1,
            budgetExhausted=False,
        ),
    ]


@router.get("/health/db")
def db_health():
    try:
        ver = get_schema_version()
        return {"status": "ok", "schema_version": ver}
    except Exception as exc:  # pragma: no cover - safety net for unexpected DB errors
        return {"status": "error", "error": str(exc)}
