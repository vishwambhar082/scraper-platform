"""
Pushes scraper results to an HTTP API.
"""
from __future__ import annotations

from typing import Iterable, Mapping

import requests


class ApiPublisher:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def publish(self, endpoint: str, records: Iterable[Mapping[str, object]]) -> requests.Response:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = requests.post(url, json=list(records), timeout=30, headers=headers)
        response.raise_for_status()
        return response

