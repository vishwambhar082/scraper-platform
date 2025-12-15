"""
API routes for Jira-Airflow integration.

Provides webhook endpoints for Jira events and callbacks from Airflow.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from src.common.logging_utils import get_logger
from src.integrations.jira_airflow_integration import (
    get_integration_service,
)

log = get_logger("integration-api")

router = APIRouter(prefix="/api/integration", tags=["integration"])


class JiraWebhookPayload(BaseModel):
    """Jira webhook payload model."""

    issue: Dict[str, Any]
    webhookEvent: str
    timestamp: int


class AirflowCallbackPayload(BaseModel):
    """Airflow callback payload model."""

    dag_id: str
    dag_run_id: str
    source: str
    run_status: str
    run_id: Optional[str] = None
    item_count: Optional[int] = None
    error: Optional[str] = None


@router.post("/jira/webhook")
async def handle_jira_webhook(
    payload: Dict[str, Any],
    request: Request,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> Dict[str, Any]:
    """
    Handle incoming Jira webhook.

    Validates webhook secret (if configured) and triggers Airflow DAG.
    """
    # Validate webhook secret (if configured)
    expected_secret = os.getenv("JIRA_WEBHOOK_SECRET")
    if expected_secret and x_webhook_secret != expected_secret:
        log.warning("Jira webhook rejected: invalid secret")
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Get integration service
    service = get_integration_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Integration service not configured (AIRFLOW_BASE_URL required)",
        )

    # Handle webhook
    try:
        result = service.handle_jira_webhook(payload)
        return result
    except Exception as exc:
        log.error("Error handling Jira webhook", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {exc}")


@router.post("/airflow/callback")
async def handle_airflow_callback(
    payload: AirflowCallbackPayload,
    x_callback_secret: str | None = Header(default=None, alias="X-Callback-Secret"),
) -> Dict[str, Any]:
    """
    Handle callback from Airflow when a run completes.

    Updates Jira issue with run status and results.
    """
    # Validate callback secret (if configured)
    expected_secret = os.getenv("AIRFLOW_CALLBACK_SECRET")
    if expected_secret and x_callback_secret != expected_secret:
        log.warning("Airflow callback rejected: invalid secret")
        raise HTTPException(status_code=401, detail="Invalid callback secret")

    # Get integration service
    service = get_integration_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Integration service not configured",
        )

    # Update Jira
    try:
        log_context = {
            "dag_id": payload.dag_id,
            "dag_run_id": payload.dag_run_id,
            "status": payload.run_status,
            "run_id": payload.run_id,
        }

        jira_issue_key: str | None = None
        dag_conf = service.fetch_dag_run_conf(payload.dag_id, payload.dag_run_id)
        if dag_conf:
            jira_issue_key = dag_conf.get("jira_issue_key") or dag_conf.get("issue_key")
            if jira_issue_key:
                log_context["jira_issue_key"] = jira_issue_key
        else:
            log_context["dag_conf_lookup"] = "missing"

        log.info("Received Airflow callback", extra=log_context)

        if jira_issue_key:
            service.update_jira_on_completion(
                issue_key=jira_issue_key,
                status=payload.run_status,
                run_id=payload.run_id,
                dag_run_id=payload.dag_run_id,
                item_count=payload.item_count,
                error=payload.error,
            )
        else:
            log.warning(
                "Unable to update Jira: issue key not found in DAG run conf",
                extra={"dag_id": payload.dag_id, "dag_run_id": payload.dag_run_id},
            )

        return {"status": "success", "message": "Callback processed", "jira_issue_key": jira_issue_key}

    except Exception as exc:
        log.error("Error handling Airflow callback", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing callback: {exc}")


@router.get("/health")
def integration_health() -> Dict[str, Any]:
    """Health check for integration service."""
    service = get_integration_service()
    jira_configured = bool(os.getenv("JIRA_BASE_URL"))
    airflow_configured = bool(os.getenv("AIRFLOW_BASE_URL"))

    return {
        "status": "ok",
        "jira_configured": jira_configured,
        "airflow_configured": airflow_configured,
        "integration_service_available": service is not None,
    }
