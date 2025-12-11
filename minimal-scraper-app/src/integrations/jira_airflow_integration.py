"""
Integration service that connects Jira webhooks to Airflow DAG triggers.

This module handles:
- Validating Jira webhook payloads
- Mapping Jira fields to Airflow DAG parameters
- Triggering Airflow DAGs
- Updating Jira with run status
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
from src.common.logging_utils import get_logger
from src.integrations.jira_client import JiraClient, get_jira_client

log = get_logger("jira-airflow-integration")

# Allowed sources (scrapers)
ALLOWED_SOURCES = {"alfabeta", "quebec", "lafa"}

# Allowed run types
ALLOWED_RUN_TYPES = {"FULL_REFRESH", "DELTA", "SINGLE_PRODUCT"}

# Allowed environments
ALLOWED_ENVIRONMENTS = {"dev", "staging", "prod"}


class IntegrationService:
    """Service that integrates Jira and Airflow."""

    def __init__(
        self,
        airflow_base_url: Optional[str] = None,
        airflow_auth: Optional[Dict[str, Any]] = None,
        jira_client: Optional[JiraClient] = None,
    ) -> None:
        """
        Initialize integration service.

        Args:
            airflow_base_url: Airflow base URL
            airflow_auth: Dict with 'token' or 'user'/'password' for Airflow auth
            jira_client: Jira client instance (optional, will create if not provided)
        """
        self.airflow_base_url = (airflow_base_url or os.getenv("AIRFLOW_BASE_URL", "")).rstrip("/")
        self.airflow_auth = airflow_auth or self._get_airflow_auth()
        self.jira_client = jira_client or get_jira_client()

        if not self.airflow_base_url:
            log.warning("Airflow base URL not configured. Integration service will not work.")

    def _get_airflow_auth(self) -> Dict[str, Any]:
        """Get Airflow authentication kwargs."""
        token = os.getenv("AIRFLOW_TOKEN")
        if token:
            return {"headers": {"Authorization": f"Bearer {token}"}}

        user = os.getenv("AIRFLOW_USER")
        password = os.getenv("AIRFLOW_PASS")
        if user and password:
            return {"auth": (user, password)}

        return {}

    def validate_jira_webhook(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Validate Jira webhook payload and extract fields.

        Returns:
            (is_valid, error_message, extracted_fields)
        """
        try:
            issue = payload.get("issue", {})
            issue_key = issue.get("key")
            fields = issue.get("fields", {})

            if not issue_key:
                return False, "Missing issue key", {}

            # Extract custom fields (adjust field IDs based on your Jira setup)
            # These are examples - you'll need to configure actual custom field IDs
            source = fields.get("customfield_source") or fields.get("Source") or ""
            run_type = fields.get("customfield_run_type") or fields.get("Run Type") or ""
            environment = fields.get("customfield_environment") or fields.get("Environment") or "prod"
            params_str = fields.get("customfield_params") or fields.get("Parameters") or "{}"

            # Validation
            if not source or source not in ALLOWED_SOURCES:
                return (
                    False,
                    f"Invalid or missing source. Must be one of: {', '.join(ALLOWED_SOURCES)}",
                    {},
                )

            if run_type and run_type not in ALLOWED_RUN_TYPES:
                return (
                    False,
                    f"Invalid run_type. Must be one of: {', '.join(ALLOWED_RUN_TYPES)}",
                    {},
                )

            if environment not in ALLOWED_ENVIRONMENTS:
                return (
                    False,
                    f"Invalid environment. Must be one of: {', '.join(ALLOWED_ENVIRONMENTS)}",
                    {},
                )

            # Parse params JSON
            import json

            try:
                params = json.loads(params_str) if params_str else {}
            except json.JSONDecodeError:
                return False, "Invalid JSON in params field", {}

            extracted = {
                "issue_key": issue_key,
                "source": source,
                "run_type": run_type or "FULL_REFRESH",
                "environment": environment,
                "params": params,
                "status": fields.get("status", {}).get("name", ""),
            }

            return True, None, extracted

        except Exception as exc:
            log.error("Error validating Jira webhook", extra={"error": str(exc)})
            return False, f"Validation error: {exc}", {}

    def map_to_airflow_dag(self, source: str) -> str:
        """Map source name to Airflow DAG ID."""
        return f"scraper_{source}"

    def trigger_airflow_dag(
        self, source: str, jira_issue_key: str, run_type: str, params: Dict[str, Any], environment: str
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Trigger Airflow DAG with Jira context.

        Returns:
            (dag_run_id, error_message)
        """
        if not self.airflow_base_url:
            return None, "Airflow base URL not configured"

        dag_id = self.map_to_airflow_dag(source)

        # Build DAG run configuration
        conf = {
            "jira_issue_key": jira_issue_key,
            "source": source,
            "run_type": run_type,
            "params": params,
            "environment": environment,
        }

        try:
            url = f"{self.airflow_base_url}/api/v1/dags/{dag_id}/dagRuns"
            resp = requests.post(
                url,
                json={"conf": conf},
                timeout=10,
                **self.airflow_auth,
            )
            resp.raise_for_status()
            result = resp.json()
            dag_run_id = result.get("dag_run_id")

            log.info(
                "Triggered Airflow DAG",
                extra={"dag_id": dag_id, "dag_run_id": dag_run_id, "jira_issue_key": jira_issue_key},
            )

            return dag_run_id, None

        except Exception as exc:
            log.error(
                "Failed to trigger Airflow DAG",
                extra={"dag_id": dag_id, "jira_issue_key": jira_issue_key, "error": str(exc)},
            )
            return None, str(exc)

    def fetch_dag_run_conf(self, dag_id: str, dag_run_id: str) -> Optional[Dict[str, Any]]:
        """Return the DAG run configuration payload from Airflow if available."""
        if not self.airflow_base_url:
            log.warning("Cannot fetch DAG run conf: AIRFLOW_BASE_URL not set")
            return None

        url = f"{self.airflow_base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        try:
            resp = requests.get(url, timeout=10, **self.airflow_auth)
            resp.raise_for_status()
            data = resp.json()
            conf = data.get("conf")
            if not isinstance(conf, dict):
                log.warning(
                    "Airflow DAG run conf missing or not a mapping",
                    extra={"dag_id": dag_id, "dag_run_id": dag_run_id},
                )
                return None
            return conf
        except Exception as exc:
            log.error(
                "Failed to fetch Airflow DAG run conf",
                extra={"dag_id": dag_id, "dag_run_id": dag_run_id, "error": str(exc)},
            )
            return None

    def update_jira_on_trigger(
        self, issue_key: str, dag_id: str, dag_run_id: str
    ) -> None:
        """Update Jira issue when Airflow DAG is triggered."""
        if not self.jira_client:
            log.warning("Jira client not configured, skipping Jira update")
            return

        try:
            comment = f"✅ Triggered Airflow DAG `{dag_id}` run `{dag_run_id}`."
            self.jira_client.add_comment(issue_key, comment)

            # Update custom field for Airflow run ID (adjust field ID)
            # self.jira_client.update_custom_field(issue_key, "customfield_airflow_run_id", dag_run_id)

        except Exception as exc:
            log.error("Failed to update Jira on trigger", extra={"issue_key": issue_key, "error": str(exc)})

    def update_jira_on_completion(
        self,
        issue_key: str,
        status: str,
        run_id: Optional[str],
        dag_run_id: Optional[str],
        item_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update Jira issue when scraper run completes."""
        if not self.jira_client:
            log.warning("Jira client not configured, skipping Jira update")
            return

        try:
            # Build comment
            status_emoji = "✅" if status == "success" else "❌"
            comment_parts = [f"{status_emoji} Scrape completed: {status.upper()}."]

            if run_id:
                comment_parts.append(f"Platform Run ID: `{run_id}`")
            if dag_run_id:
                comment_parts.append(f"Airflow DAG Run: `{dag_run_id}`")
            if item_count is not None:
                comment_parts.append(f"Items: {item_count:,}")
            if error:
                comment_parts.append(f"Error: {error}")

            comment = " ".join(comment_parts)
            self.jira_client.add_comment(issue_key, comment)

            # Update custom fields
            # self.jira_client.update_custom_field(issue_key, "customfield_run_status", status.upper())
            # if run_id:
            #     self.jira_client.update_custom_field(issue_key, "customfield_run_id", run_id)

            # Transition issue (adjust transition IDs based on your workflow)
            # if status == "success":
            #     self.jira_client.transition_issue(issue_key, "transition_id_for_completed")
            # elif status == "failed":
            #     self.jira_client.transition_issue(issue_key, "transition_id_for_failed")

        except Exception as exc:
            log.error(
                "Failed to update Jira on completion",
                extra={"issue_key": issue_key, "error": str(exc)},
            )

    def handle_jira_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main handler for Jira webhook events.

        Returns:
            Response dict with status and message
        """
        # Validate webhook
        is_valid, error_msg, fields = self.validate_jira_webhook(payload)

        if not is_valid:
            issue_key = payload.get("issue", {}).get("key", "UNKNOWN")
            if self.jira_client and issue_key != "UNKNOWN":
                try:
                    self.jira_client.add_comment(
                        issue_key, f"❌ Validation failed: {error_msg}"
                    )
                except Exception:
                    pass
            return {"status": "error", "message": error_msg}

        issue_key = fields["issue_key"]
        source = fields["source"]
        run_type = fields["run_type"]
        params = fields["params"]
        environment = fields["environment"]

        # Trigger Airflow
        dag_run_id, error = self.trigger_airflow_dag(
            source=source,
            jira_issue_key=issue_key,
            run_type=run_type,
            params=params,
            environment=environment,
        )

        if error:
            if self.jira_client:
                try:
                    self.jira_client.add_comment(
                        issue_key, f"❌ Failed to trigger Airflow: {error}"
                    )
                except Exception:
                    pass
            return {"status": "error", "message": f"Failed to trigger Airflow: {error}"}

        # Update Jira
        dag_id = self.map_to_airflow_dag(source)
        self.update_jira_on_trigger(issue_key, dag_id, dag_run_id)

        return {
            "status": "success",
            "message": f"Triggered Airflow DAG {dag_id}",
            "dag_run_id": dag_run_id,
        }


def get_integration_service() -> Optional[IntegrationService]:
    """Get configured integration service or None if not configured."""
    airflow_url = os.getenv("AIRFLOW_BASE_URL")
    if not airflow_url:
        return None
    return IntegrationService()

