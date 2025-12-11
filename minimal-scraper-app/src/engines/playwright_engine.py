"""Lightweight Playwright helpers with retry + jitter semantics.

The real Playwright dependency is optional; these utilities operate against any
object exposing ``goto``/``wait_for_timeout``/``content``-like methods, which
keeps them testable with fakes while still providing reliability primitives
for live scrapes.
"""

import asyncio
import random
from typing import Awaitable, Callable, Optional

from src.common.logging_utils import get_logger, sanitize_for_log, safe_log

log = get_logger("playwright-engine")

DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.0
DEFAULT_JITTER = 0.5
DEFAULT_WAIT_MS = 250


def _jitter_delay(base: float, jitter: float) -> float:
    return max(0.0, base + random.uniform(0, jitter))


async def _sleep(delay: float, page) -> None:
    try:
        await page.wait_for_timeout(int(delay * 1000))
    except Exception:
        await asyncio.sleep(delay)


async def _looks_rate_limited(page) -> bool:
    try:
        html = await page.content()
    except Exception:
        return False
    body = (html or "").lower()
    return "429" in body or "too many requests" in body


async def goto_with_retry(
    page,
    url: str,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    jitter: float = DEFAULT_JITTER,
    wait_ms: int = DEFAULT_WAIT_MS,
    on_proxy_failover: Optional[Callable[[], Awaitable[None]]] = None,
):
    """Navigate with retry/backoff and optional proxy failover callback."""

    attempt = 0
    last_exc: Optional[Exception] = None

    while attempt < retries:
        try:
            response = await page.goto(url)
            wait_delay_ms = int(_jitter_delay(wait_ms / 1000.0, jitter) * 1000)
            await page.wait_for_timeout(wait_delay_ms)

            status = getattr(response, "status", lambda: None)
            if callable(status):
                status = status()

            if status == 429 or await _looks_rate_limited(page):
                raise RuntimeError("rate limited or blocked")
            return
        except Exception as exc:  # pragma: no cover - resilience guard
            last_exc = exc
            attempt += 1

            if on_proxy_failover and attempt == retries // 2:
                safe_log(
                    log,
                    "warning",
                    "Attempting proxy failover during Playwright navigation",
                    extra=sanitize_for_log({"url": url}),
                )
                await on_proxy_failover()

            if attempt >= retries:
                break

            delay = _jitter_delay(backoff * attempt, jitter)
            safe_log(
                log,
                "info",
                "Retrying goto",
                extra=sanitize_for_log({"url": url, "attempt": attempt, "delay": delay}),
            )
            await _sleep(delay, page)

    if last_exc:
        raise last_exc
