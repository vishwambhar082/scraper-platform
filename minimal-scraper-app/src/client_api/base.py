from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests


@dataclass
class ClientAPIError(Exception):
    """Raised when the API returns a non-successful response."""

    status_code: int
    message: str
    response_body: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - delegated to dataclass repr
        return f"APIError({self.status_code}): {self.message}"


class BaseAPIClient:
    """Shared HTTP plumbing for the external client SDK."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.session = session or requests.Session()
        self.headers = headers or {}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = urljoin(self.base_url, path.lstrip("/"))
        request_headers = {**self.headers, **kwargs.pop("headers", {})}
        response = self.session.request(method, url, timeout=self.timeout, headers=request_headers, **kwargs)

        if response.status_code >= 400:
            raise ClientAPIError(
                status_code=response.status_code,
                message=f"Request failed for {url}",
                response_body=response.text,
            )

        content_type = response.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            return response.json()
        return response.text
