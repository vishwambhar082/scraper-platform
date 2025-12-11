"""
Jira API client for updating issues and reading fields.

Handles authentication, API calls, and error handling for Jira interactions.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
from src.common.logging_utils import get_logger

log = get_logger("jira-client")


class JiraClient:
    """Client for interacting with Jira REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
    ) -> None:
        """
        Initialize Jira client.

        Args:
            base_url: Jira base URL (e.g., https://yourcompany.atlassian.net)
            username: Jira username/email
            api_token: Jira API token (from https://id.atlassian.com/manage-profile/security/api-tokens)
        """
        self.base_url = (base_url or os.getenv("JIRA_BASE_URL", "")).rstrip("/")
        self.username = username or os.getenv("JIRA_USERNAME", "")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN", "")

        if not self.base_url or not self.username or not self.api_token:
            log.warning(
                "Jira client initialized without credentials. Jira updates will be disabled.",
                extra={"base_url": bool(self.base_url), "username": bool(self.username)},
            )

    def _get_auth(self) -> tuple[str, str]:
        """Get HTTP basic auth tuple."""
        return (self.username, self.api_token)

    def _request(
        self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Jira API."""
        if not self.base_url:
            raise RuntimeError("Jira base URL not configured")

        url = f"{self.base_url}/rest/api/3/{endpoint}"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        try:
            resp = requests.request(
                method=method,
                url=url,
                auth=self._get_auth(),
                headers=headers,
                json=json_data,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.exceptions.RequestException as exc:
            log.error(
                "Jira API request failed",
                extra={"method": method, "endpoint": endpoint, "error": str(exc)},
            )
            raise

    def add_comment(self, issue_key: str, comment: str) -> None:
        """Add a comment to a Jira issue."""
        try:
            self._request(
                "POST",
                f"issue/{issue_key}/comment",
                json_data={"body": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}},
            )
            log.info("Added comment to Jira issue", extra={"issue_key": issue_key})
        except Exception as exc:
            log.error("Failed to add Jira comment", extra={"issue_key": issue_key, "error": str(exc)})
            raise

    def update_custom_field(self, issue_key: str, field_id: str, value: Any) -> None:
        """
        Update a custom field on a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., SCRAPE-123)
            field_id: Custom field ID (e.g., customfield_10001) or field name
            value: Value to set
        """
        try:
            # Jira API expects fields in update format
            self._request(
                "PUT",
                f"issue/{issue_key}",
                json_data={"fields": {field_id: value}},
            )
            log.info(
                "Updated Jira custom field",
                extra={"issue_key": issue_key, "field_id": field_id},
            )
        except Exception as exc:
            log.error(
                "Failed to update Jira custom field",
                extra={"issue_key": issue_key, "field_id": field_id, "error": str(exc)},
            )
            raise

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        """
        Transition a Jira issue to a new status.

        Args:
            issue_key: Jira issue key
            transition_id: Transition ID (can be found via GET /issue/{key}/transitions)
        """
        try:
            self._request(
                "POST",
                f"issue/{issue_key}/transitions",
                json_data={"transition": {"id": transition_id}},
            )
            log.info(
                "Transitioned Jira issue",
                extra={"issue_key": issue_key, "transition_id": transition_id},
            )
        except Exception as exc:
            log.error(
                "Failed to transition Jira issue",
                extra={"issue_key": issue_key, "transition_id": transition_id, "error": str(exc)},
            )
            raise

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get full issue details."""
        return self._request("GET", f"issue/{issue_key}")

    def get_issue_fields(self, issue_key: str) -> Dict[str, Any]:
        """Get issue fields (convenience method)."""
        issue = self.get_issue(issue_key)
        return issue.get("fields", {})


def get_jira_client() -> Optional[JiraClient]:
    """Get configured Jira client or None if not configured."""
    base_url = os.getenv("JIRA_BASE_URL")
    if not base_url:
        return None
    return JiraClient()

