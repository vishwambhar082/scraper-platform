from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/airflow", tags=["airflow"])


def _get_airflow_base_url() -> str | None:
    return os.getenv("AIRFLOW_BASE_URL")


def _get_auth_kwargs() -> Dict[str, Any]:
    """
    Optional auth:
      - AIRFLOW_TOKEN: Bearer token
      - AIRFLOW_USER / AIRFLOW_PASS: basic auth
    """
    token = os.getenv("AIRFLOW_TOKEN")
    if token:
        return {"headers": {"Authorization": f"Bearer {token}"}}

    user = os.getenv("AIRFLOW_USER")
    pw = os.getenv("AIRFLOW_PASS")
    if user and pw:
        return {"auth": (user, pw)}

    return {}


@router.get("/runs")
def proxy_runs(limit: int = 20) -> Dict[str, Any]:
    """
    GET /api/airflow/runs

    - If AIRFLOW_BASE_URL unset: return stub payload to keep dashboard working.
    - If set: proxy to Airflow's /dags + /dagRuns APIs and return flattened list.
    """
    base_url = _get_airflow_base_url()
    if not base_url:
        return {
            "status": "ok",
            "mode": "stub",
            "message": "Airflow proxy stub (AIRFLOW_BASE_URL not set)",
            "runs": [
                {
                    "dag_id": "scraper_alfabeta",
                    "run_id": "manual__2024-05-01T10:00:00+00:00",
                    "state": "success",
                }
            ],
        }

    base_url = base_url.rstrip("/")
    auth_kwargs = _get_auth_kwargs()

    try:
        dags_resp = requests.get(
            f"{base_url}/api/v1/dags?limit={limit}",
            timeout=10,
            **auth_kwargs,
        )
        dags_resp.raise_for_status()
        dags = dags_resp.json().get("dags", [])
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to list Airflow DAGs: {exc}",
        )

    runs: List[Dict[str, Any]] = []
    for dag in dags:
        dag_id = dag.get("dag_id")
        if not dag_id:
            continue
        try:
            r = requests.get(
                f"{base_url}/api/v1/dags/{dag_id}/dagRuns?limit=3",
                timeout=10,
                **auth_kwargs,
            )
            if not r.ok:
                continue
            for dr in r.json().get("dag_runs", []):
                runs.append(
                    {
                        "dag_id": dag_id,
                        "run_id": dr.get("dag_run_id"),
                        "state": dr.get("state"),
                        "start_date": dr.get("start_date"),
                        "end_date": dr.get("end_date"),
                    }
                )
        except Exception:
            continue

    return {
        "status": "ok",
        "mode": "live",
        "runs": runs,
    }
