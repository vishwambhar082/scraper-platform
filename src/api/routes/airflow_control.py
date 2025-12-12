"""
API routes for Airflow control operations.

Allows triggering DAGs, pausing/unpausing, and other Airflow operations.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.common.logging_utils import get_logger

log = get_logger("airflow-control")

router = APIRouter(prefix="/api/airflow", tags=["airflow"])


def _get_airflow_base_url() -> str | None:
    return os.getenv("AIRFLOW_BASE_URL")


def _get_auth_kwargs() -> Dict[str, Any]:
    """Get Airflow authentication kwargs."""
    token = os.getenv("AIRFLOW_TOKEN")
    if token:
        return {"headers": {"Authorization": f"Bearer {token}"}}

    user = os.getenv("AIRFLOW_USER")
    pw = os.getenv("AIRFLOW_PASS")
    if user and pw:
        return {"auth": (user, pw)}

    return {}


class TriggerDagRequest(BaseModel):
    dag_id: str
    conf: Dict[str, Any] = {}


@router.post("/trigger")
def trigger_dag(request: TriggerDagRequest) -> Dict[str, Any]:
    """
    Trigger an Airflow DAG run.

    Args:
        request: DAG trigger request with dag_id and optional conf

    Returns:
        DAG run information
    """
    base_url = _get_airflow_base_url()
    if not base_url:
        raise HTTPException(
            status_code=503,
            detail="Airflow not configured (AIRFLOW_BASE_URL not set)",
        )

    base_url = base_url.rstrip("/")
    auth_kwargs = _get_auth_kwargs()

    try:
        url = f"{base_url}/api/v1/dags/{request.dag_id}/dagRuns"
        resp = requests.post(
            url,
            json={"conf": request.conf},
            timeout=10,
            **auth_kwargs,
        )
        resp.raise_for_status()
        result = resp.json()

        log.info("Triggered Airflow DAG", extra={"dag_id": request.dag_id, "dag_run_id": result.get("dag_run_id")})

        return {
            "success": True,
            "dag_id": request.dag_id,
            "dag_run_id": result.get("dag_run_id"),
            "message": f"DAG {request.dag_id} triggered successfully",
        }

    except requests.exceptions.RequestException as exc:
        log.error("Failed to trigger Airflow DAG", extra={"dag_id": request.dag_id, "error": str(exc)})
        raise HTTPException(
            status_code=502,
            detail=f"Failed to trigger Airflow DAG: {exc}",
        )


@router.post("/dag/{dag_id}/pause")
def pause_dag(dag_id: str) -> Dict[str, Any]:
    """Pause an Airflow DAG."""
    base_url = _get_airflow_base_url()
    if not base_url:
        raise HTTPException(status_code=503, detail="Airflow not configured")

    auth_kwargs = _get_auth_kwargs()
    try:
        url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}"
        resp = requests.patch(
            url,
            json={"is_paused": True},
            timeout=10,
            **auth_kwargs,
        )
        resp.raise_for_status()
        return {"success": True, "message": f"DAG {dag_id} paused"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to pause DAG: {exc}")


@router.post("/dag/{dag_id}/unpause")
def unpause_dag(dag_id: str) -> Dict[str, Any]:
    """Unpause an Airflow DAG."""
    base_url = _get_airflow_base_url()
    if not base_url:
        raise HTTPException(status_code=503, detail="Airflow not configured")

    auth_kwargs = _get_auth_kwargs()
    try:
        url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}"
        resp = requests.patch(
            url,
            json={"is_paused": False},
            timeout=10,
            **auth_kwargs,
        )
        resp.raise_for_status()
        return {"success": True, "message": f"DAG {dag_id} unpaused"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to unpause DAG: {exc}")
