from __future__ import annotations

from typing import List, Optional

from src.api import models
from src.client_api.base import BaseAPIClient


class ScraperClient(BaseAPIClient):
    """Client for run metadata and execution-facing endpoints."""

    def list_runs(self) -> List[models.RunSummary]:
        payload = self._request("GET", "/api/runs")
        return [models.RunSummary.model_validate(item) for item in payload]

    def get_run(self, run_id: str) -> models.RunDetail:
        payload = self._request("GET", f"/api/runs/{run_id}")
        return models.RunDetail.model_validate(payload)

    def get_steps(self, run_id: str) -> List[models.RunStep]:
        payload = self._request("GET", f"/api/steps/{run_id}")
        return [models.RunStep.model_validate(item) for item in payload]

    def airflow_runs(self) -> dict:
        """Return proxied Airflow run metadata (stubbed for now)."""

        return self._request("GET", "/api/airflow/runs")

    def trigger_run(self, dag_id: str, conf: Optional[dict] = None) -> dict:
        """Placeholder hook to trigger new scraper runs when exposed server-side."""

        return self._request("POST", f"/api/airflow/dags/{dag_id}/runs", json=conf or {})
