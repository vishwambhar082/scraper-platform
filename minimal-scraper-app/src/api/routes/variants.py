from fastapi import APIRouter, Header, Query

from src.api.data.run_store import list_variant_benchmarks
from src.api.models import VariantBenchmark

router = APIRouter(prefix="/api/variants", tags=["variants"])


@router.get("/benchmarks", response_model=list[VariantBenchmark])
def get_variant_benchmarks(
    source: str | None = Query(None),
    tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> list[VariantBenchmark]:
    """
    Return aggregated performance metrics grouped by variant.
    
    Tenant isolation: If tenant_id is provided, only returns benchmarks for that tenant.
    If not provided, returns benchmarks for 'default' tenant.
    """
    effective_tenant_id = tenant_id or "default"
    return list_variant_benchmarks(source, tenant_id=effective_tenant_id)
