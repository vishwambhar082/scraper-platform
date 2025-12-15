"""
HTTP Engine implementation using requests.

This is a complete, production-ready HTTP engine that extends BaseEngine.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests
from requests import Response

from src.common.logging_utils import get_logger
from src.engines.base_engine import BaseEngine, EngineConfig, EngineError, EngineResult

log = get_logger("http-engine")


class HttpEngine(BaseEngine):
    """HTTP engine using requests library."""

    def __init__(self, config: EngineConfig):
        super().__init__(config)
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """Get or create requests session."""
        if self._session is None:
            self._session = requests.Session()
            if self.config.headers:
                self._session.headers.update(self.config.headers)
        return self._session

    def _build_proxies(self) -> Optional[Dict[str, str]]:
        """Convert proxy string to requests proxies dict."""
        if not self.config.proxy:
            return None
        return {"http": self.config.proxy, "https": self.config.proxy}

    def fetch(self, url: str, method: str = "GET", **kwargs: Any) -> EngineResult:
        """
        Fetch content from URL.

        Args:
            url: Target URL
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional request parameters (data, json, params, etc.)

        Returns:
            EngineResult with content

        Raises:
            EngineError on failure
        """
        if self._closed:
            raise EngineError("Engine has been closed")

        session = self._get_session()
        proxies = self._build_proxies()

        try:
            start = time.time()
            response: Response = session.request(
                method=method,
                url=url,
                timeout=self.config.timeout,
                proxies=proxies,
                **kwargs,
            )
            elapsed = time.time() - start

            # Check for rate limiting
            if response.status_code == 429:
                raise EngineError(
                    f"Rate limited: {response.status_code}",
                    url=url,
                    status_code=response.status_code,
                )

            # Check for server errors that might be transient
            if response.status_code >= 500:
                raise EngineError(
                    f"Server error: {response.status_code}",
                    url=url,
                    status_code=response.status_code,
                )

            return EngineResult(
                url=str(response.url),
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers),
                elapsed_seconds=elapsed,
                metadata={
                    "method": method,
                    "final_url": str(response.url),
                },
            )

        except requests.Timeout as exc:
            raise EngineError(f"Request timeout: {exc}", url=url) from exc
        except requests.ConnectionError as exc:
            raise EngineError(f"Connection error: {exc}", url=url) from exc
        except requests.RequestException as exc:
            raise EngineError(f"Request failed: {exc}", url=url) from exc

    def cleanup(self) -> None:
        """Close session and clean up resources."""
        if self._session:
            self._session.close()
            self._session = None
        self._mark_closed()


__all__ = ["HttpEngine"]

