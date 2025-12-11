from __future__ import annotations

from fastapi import APIRouter, Header

from src.api.data.run_store import get_run_steps
from src.api.models import RunStep

router = APIRouter(prefix="/api/steps", tags=["steps"])


@router.get("/{run_id}", response_model=list[RunStep])
def get_steps(run_id: str, tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")) -> list[RunStep]:
    """Return the executed steps for a run."""
    if not isinstance(tenant_id, (str, type(None))):
        tenant_id = None
    return get_run_steps(run_id, tenant_id=tenant_id)
