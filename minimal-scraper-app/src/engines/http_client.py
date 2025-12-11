"""
HTTP client engine for simple/static sites.

This is intentionally simple but robust:

- Uses requests.Session for connection reuse
- Optional SimpleRateLimiter integration
- Retries with backoff on transient failures
- Proxy support via a single proxy string
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import requests
from requests import Response

from src.common.logging_utils import sanitize_for_log, safe_log
from .rate_limiter import SimpleRateLimiter

log = logging.getLogger("http-engine")


@dataclass
class HttpRequestConfig:
    """
    Configuration for a single HTTP request.

    Typical usage:
        cfg = HttpRequestConfig(
            url="https://example.com",
            proxy="http://user:pass@host:port",
            max_retries=3,
            backoff_seconds=1.5,
        )
    """

    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    data: Optional[Any] = None
    json: Optional[Any] = None
    timeout: float = 30.0
    proxy: Optional[str] = None
    max_retries: int = 3
    backoff_seconds: float = 1.0
    allowed_statuses: Sequence[int] = (200,)


@dataclass
class HttpResult:
    """
    Result of a successful HTTP request.
    """

    url: str
    status_code: int
    text: str
    headers: Dict[str, str]
    elapsed_seconds: float


def _build_proxies(proxy: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Convert a single proxy string into the requests proxies dict.

    Example:
        proxy="http://user:pass@host:port" →
            {"http": "...", "https": "..."}
    """
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def send_request(
    cfg: HttpRequestConfig,
    *,
    session: Optional[requests.Session] = None,
    rate_limiter: Optional[SimpleRateLimiter] = None,
) -> HttpResult:
    """
    Core HTTP request function with retries and optional rate limiting.

    This is the only function pipelines should call directly.

    Raises:
        RuntimeError if all retries are exhausted or status is not allowed.
    """

    sess = session or requests.Session()
    proxies = _build_proxies(cfg.proxy)

    attempt = 0
    last_exc: Optional[Exception] = None

    while attempt <= cfg.max_retries:
        if rate_limiter is not None:
            rate_limiter.wait()

        attempt += 1
        try:
            start = time.time()
            resp: Response = sess.request(
                method=cfg.method,
                url=cfg.url,
                headers=cfg.headers,
                params=cfg.params,
                data=cfg.data,
                json=cfg.json,
                timeout=cfg.timeout,
                proxies=proxies,
            )
            elapsed = time.time() - start

            if resp.status_code not in cfg.allowed_statuses:
                safe_log(
                    log,
                    "warning",
                    "HTTP request returned unexpected status",
                    extra=sanitize_for_log(
                        {
                            "method": cfg.method,
                            "url": cfg.url,
                            "status_code": resp.status_code,
                            "attempt": attempt,
                            "max_retries": cfg.max_retries,
                        }
                    ),
                )
                # treat this as a failure that can be retried
                last_exc = RuntimeError(
                    f"Unexpected status {resp.status_code} for {cfg.url}"
                )
            else:
                # success
                return HttpResult(
                    url=str(resp.url),
                    status_code=resp.status_code,
                    text=resp.text,
                    headers=dict(resp.headers),
                    elapsed_seconds=elapsed,
                )

        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            safe_log(
                log,
                "warning",
                "HTTP request failed",
                extra=sanitize_for_log(
                    {
                        "method": cfg.method,
                        "url": cfg.url,
                        "error": type(exc).__name__,
                        "attempt": attempt,
                        "max_retries": cfg.max_retries,
                    }
                ),
            )

        # if we’re here, either status was bad or exception happened
        if attempt <= cfg.max_retries:
            time.sleep(cfg.backoff_seconds * attempt)

    raise RuntimeError(
        f"HTTP request failed after {cfg.max_retries} retries for {cfg.url}"
    ) from last_exc
