from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Query, Header
from psycopg2.extras import RealDictCursor

from src.common import db
from src.common.logging_utils import get_logger

log = get_logger("costs-api")

router = APIRouter(prefix="/api/costs", tags=["costs"])


def _serialize_cost(row: Dict[str, Any]) -> Dict[str, Any]:
    cost_value = row.get("cost_usd")
    if isinstance(cost_value, Decimal):
        cost_value = float(cost_value)
    return {
        "source": row["source"],
        "run_id": row["run_id"],
        "cost_usd": cost_value,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


@router.get("")
def get_costs(
    source: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
) -> dict:
    """
    Read run cost tracking data from Postgres.
    
    Tenant isolation: If tenant_id is provided, only returns costs for that tenant.
    If not provided, returns costs for 'default' tenant.
    """
    # Enforce tenant isolation - default to 'default' if not provided
    effective_tenant_id = tenant_id or "default"
    
    # Build where clauses - handle tenant_id for both tables
    # run_costs may not have tenant_id column yet, so we check cost_tracking first
    clauses_run_costs = []
    clauses_cost_tracking = ["tenant_id = %s"]
    params: List[Any] = [effective_tenant_id]
    
    if source:
        clauses_run_costs.append("source = %s")
        clauses_cost_tracking.append("source = %s")
        params.append(source)
    
    where_run_costs = " AND ".join(clauses_run_costs) if clauses_run_costs else "1=1"
    where_cost_tracking = " AND ".join(clauses_cost_tracking)

    with db.transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if run_costs has tenant_id column
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'scraper' 
                AND table_name = 'run_costs' 
                AND column_name = 'tenant_id'
            """)
            has_tenant_id = cur.fetchone() is not None
            
            # Build appropriate where clause for run_costs
            if has_tenant_id:
                where_run_costs = where_cost_tracking
                params_run_costs = params
            else:
                params_run_costs = params[1:] if len(params) > 1 else []  # Remove tenant_id param
            
            # Try cost_tracking table first (has tenant_id and detailed breakdown)
            cur.execute(
                f"""
                SELECT 
                    source, 
                    run_id,
                    (proxy_cost_usd + compute_cost_usd + other_cost_usd) AS cost_usd,
                    created_at AS updated_at
                FROM scraper.cost_tracking
                WHERE {where_cost_tracking}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (*params, limit, offset),
            )
            rows = cur.fetchall()
            
            # If no rows, try run_costs table (simplified)
            if not rows:
                cur.execute(
                    f"""
                    SELECT source, run_id, cost_usd, updated_at
                    FROM scraper.run_costs
                    WHERE {where_run_costs}
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (*params_run_costs, limit, offset),
                )
                rows = cur.fetchall()

            # Get total count
            if has_tenant_id:
                count_where = where_cost_tracking
                count_params = params
            else:
                count_where = where_run_costs
                count_params = params_run_costs
            
            cur.execute(
                f"""
                SELECT COUNT(*) AS total 
                FROM (
                    SELECT 1 FROM scraper.cost_tracking WHERE {where_cost_tracking}
                    UNION ALL
                    SELECT 1 FROM scraper.run_costs WHERE {count_where}
                ) AS combined
                """,
                count_params + params,  # Combine params
            )
            total = cur.fetchone()["total"]

    return {
        "costs": [_serialize_cost(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "tenant_id": effective_tenant_id,
    }


@router.get("/stats")
def get_cost_stats(
    source: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
) -> dict:
    """
    Get aggregated cost statistics.
    
    Returns:
        - total_cost: Total cost in USD
        - average_cost: Average cost per run
        - by_source: Cost breakdown by source
        - daily_trends: Daily cost aggregation
        - cost_per_source: Average cost per source
    """
    effective_tenant_id = tenant_id or "default"
    
    clauses = ["tenant_id = %s", "updated_at >= NOW() - INTERVAL '%s days'"]
    params: List[Any] = [effective_tenant_id, days]
    
    if source:
        clauses.append("source = %s")
        params.append(source)
    
    where_clause = " AND ".join(clauses)
    
    with db.transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get aggregated stats
            cur.execute(
                f"""
                SELECT 
                    COUNT(*) as run_count,
                    SUM(cost_usd) as total_cost,
                    AVG(cost_usd) as avg_cost,
                    MIN(cost_usd) as min_cost,
                    MAX(cost_usd) as max_cost,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cost_usd) as median_cost
                FROM (
                    SELECT source, run_id, cost_usd, updated_at
                    FROM scraper.run_costs
                    WHERE {where_clause}
                    UNION ALL
                    SELECT 
                        source, 
                        run_id,
                        (proxy_cost_usd + compute_cost_usd + other_cost_usd) AS cost_usd,
                        created_at AS updated_at
                    FROM scraper.cost_tracking
                    WHERE {where_clause}
                ) AS combined
                """,
                params,
            )
            stats = cur.fetchone()
            
            # Get breakdown by source
            cur.execute(
                f"""
                SELECT 
                    source,
                    COUNT(*) as run_count,
                    SUM(cost_usd) as total_cost,
                    AVG(cost_usd) as avg_cost
                FROM (
                    SELECT source, run_id, cost_usd, updated_at
                    FROM scraper.run_costs
                    WHERE {where_clause}
                    UNION ALL
                    SELECT 
                        source, 
                        run_id,
                        (proxy_cost_usd + compute_cost_usd + other_cost_usd) AS cost_usd,
                        created_at AS updated_at
                    FROM scraper.cost_tracking
                    WHERE {where_clause}
                ) AS combined
                GROUP BY source
                ORDER BY total_cost DESC
                """,
                params,
            )
            by_source = cur.fetchall()
            
            # Get daily trends
            cur.execute(
                f"""
                SELECT 
                    DATE(updated_at) as date,
                    COUNT(*) as run_count,
                    SUM(cost_usd) as daily_cost,
                    AVG(cost_usd) as avg_cost
                FROM (
                    SELECT source, run_id, cost_usd, updated_at
                    FROM scraper.run_costs
                    WHERE {where_clause}
                    UNION ALL
                    SELECT 
                        source, 
                        run_id,
                        (proxy_cost_usd + compute_cost_usd + other_cost_usd) AS cost_usd,
                        created_at AS updated_at
                    FROM scraper.cost_tracking
                    WHERE {where_clause}
                ) AS combined
                GROUP BY DATE(updated_at)
                ORDER BY date DESC
                """,
                params,
            )
            daily_trends = cur.fetchall()
    
    def _float_or_zero(val):
        if val is None:
            return 0.0
        if isinstance(val, Decimal):
            return float(val)
        return float(val)
    
    return {
        "summary": {
            "total_cost": _float_or_zero(stats.get("total_cost")),
            "average_cost": _float_or_zero(stats.get("avg_cost")),
            "min_cost": _float_or_zero(stats.get("min_cost")),
            "max_cost": _float_or_zero(stats.get("max_cost")),
            "median_cost": _float_or_zero(stats.get("median_cost")),
            "run_count": int(stats.get("run_count") or 0),
        },
        "by_source": [
            {
                "source": row["source"],
                "run_count": int(row.get("run_count") or 0),
                "total_cost": _float_or_zero(row.get("total_cost")),
                "average_cost": _float_or_zero(row.get("avg_cost")),
            }
            for row in by_source
        ],
        "daily_trends": [
            {
                "date": row["date"].isoformat() if row.get("date") else None,
                "run_count": int(row.get("run_count") or 0),
                "daily_cost": _float_or_zero(row.get("daily_cost")),
                "average_cost": _float_or_zero(row.get("avg_cost")),
            }
            for row in daily_trends
        ],
        "period_days": days,
        "tenant_id": effective_tenant_id,
    }


@router.get("/breakdown")
def get_cost_breakdown(
    source: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
) -> dict:
    """
    Get detailed cost breakdown (proxy, compute, other).
    
    Returns cost breakdown by category from cost_tracking table.
    """
    effective_tenant_id = tenant_id or "default"
    
    clauses = ["tenant_id = %s", "created_at >= NOW() - INTERVAL '%s days'"]
    params: List[Any] = [effective_tenant_id, days]
    
    if source:
        clauses.append("source = %s")
        params.append(source)
    
    where_clause = " AND ".join(clauses)
    
    with db.transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT 
                    source,
                    SUM(proxy_cost_usd) as total_proxy_cost,
                    SUM(compute_cost_usd) as total_compute_cost,
                    SUM(other_cost_usd) as total_other_cost,
                    SUM(proxy_cost_usd + compute_cost_usd + other_cost_usd) as total_cost,
                    COUNT(*) as run_count
                FROM scraper.cost_tracking
                WHERE {where_clause}
                GROUP BY source
                ORDER BY total_cost DESC
                """,
                params,
            )
            breakdown = cur.fetchall()
            
            # Overall totals
            cur.execute(
                f"""
                SELECT 
                    SUM(proxy_cost_usd) as total_proxy_cost,
                    SUM(compute_cost_usd) as total_compute_cost,
                    SUM(other_cost_usd) as total_other_cost,
                    SUM(proxy_cost_usd + compute_cost_usd + other_cost_usd) as total_cost
                FROM scraper.cost_tracking
                WHERE {where_clause}
                """,
                params,
            )
            totals = cur.fetchone()
    
    def _float_or_zero(val):
        if val is None:
            return 0.0
        if isinstance(val, Decimal):
            return float(val)
        return float(val)
    
    return {
        "by_source": [
            {
                "source": row["source"],
                "proxy_cost": _float_or_zero(row.get("total_proxy_cost")),
                "compute_cost": _float_or_zero(row.get("total_compute_cost")),
                "other_cost": _float_or_zero(row.get("total_other_cost")),
                "total_cost": _float_or_zero(row.get("total_cost")),
                "run_count": int(row.get("run_count") or 0),
            }
            for row in breakdown
        ],
        "totals": {
            "proxy_cost": _float_or_zero(totals.get("total_proxy_cost")),
            "compute_cost": _float_or_zero(totals.get("total_compute_cost")),
            "other_cost": _float_or_zero(totals.get("total_other_cost")),
            "total_cost": _float_or_zero(totals.get("total_cost")),
        },
        "period_days": days,
        "tenant_id": effective_tenant_id,
    }
