from __future__ import annotations

from typing import List

from src.api import models
from src.client_api.base import BaseAPIClient


class HealthClient(BaseAPIClient):
    """Client focused on liveness and source health signals."""

    def health(self) -> bool:
        payload = self._request("GET", "/health")
        return isinstance(payload, dict) and payload.get("status") == "ok"

    def source_health(self) -> List[models.SourceHealth]:
        payload = self._request("GET", "/api/source-health")
        return [models.SourceHealth.model_validate(item) for item in payload]
