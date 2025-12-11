from __future__ import annotations

from typing import Dict, Any, Optional
import logging
import time
import requests

logger = logging.getLogger(__name__)


class HttpEngine:
    """Thin wrapper around requests with retries and backoff."""

    def __init__(
        self,
        timeout: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.default_headers = default_headers or {}

    def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        merged_headers = {**self.default_headers, **(headers or {})}
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("HTTP %s %s (attempt %s)", method, url, attempt)
                resp = requests.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    params=params,
                    data=data,
                    json=json_body,
                    timeout=self.timeout,
                    proxies=proxies,
                )
                if 200 <= resp.status_code < 300:
                    logger.debug("HTTP %s %s -> %s", method, url, resp.status_code)
                    return resp
                logger.warning(
                    "HTTP %s %s -> %s (attempt %s)",
                    method,
                    url,
                    resp.status_code,
                    attempt,
                )
            except requests.RequestException as exc:
                logger.warning(
                    "HTTP %s %s failed (%s) attempt=%s",
                    method,
                    url,
                    exc,
                    attempt,
                )
            if attempt < self.max_retries:
                sleep_for = self.backoff_factor * attempt
                time.sleep(sleep_for)
        raise RuntimeError(f"Failed to fetch {url} after {self.max_retries} attempts")


__all__ = ["HttpEngine"]
