"""
Base engine abstraction for all scraping engines.

This provides a unified interface that all engines (HTTP, Selenium, Playwright, Groq)
must implement, ensuring consistent error handling, retry logic, and dependency injection.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence

from src.common.logging_utils import get_logger, safe_log

log = get_logger("base-engine")


@dataclass
class EngineConfig:
    """Configuration for engine initialization."""

    proxy: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.0
    retry_jitter: float = 0.5
    headers: Optional[Dict[str, str]] = None
    rate_limiter: Optional[Any] = None  # SimpleRateLimiter


@dataclass
class EngineResult:
    """Unified result from any engine."""

    url: str
    status_code: int
    content: str  # HTML/text content
    headers: Dict[str, str]
    elapsed_seconds: float
    metadata: Dict[str, Any]  # Engine-specific metadata (screenshots, cookies, etc.)


class EngineError(Exception):
    """Base exception for all engine errors."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        retries_exhausted: bool = False,
    ):
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.retries_exhausted = retries_exhausted


class RateLimitError(EngineError):
    """Raised when rate limit is detected."""

    pass


class BaseEngine(ABC):
    """
    Abstract base class for all scraping engines.

    All engines must implement:
    - fetch() - Core fetch operation
    - cleanup() - Resource cleanup
    """

    def __init__(self, config: EngineConfig):
        self.config = config
        self._closed = False

    @abstractmethod
    def fetch(self, url: str, **kwargs: Any) -> EngineResult:
        """
        Fetch content from a URL.

        Args:
            url: Target URL
            **kwargs: Engine-specific parameters

        Returns:
            EngineResult with content and metadata

        Raises:
            EngineError on failure
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources (close connections, browsers, etc.)."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.cleanup()
        return False

    def _should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if an error should be retried."""
        if attempt >= self.config.max_retries:
            return False

        # Always retry on rate limit errors
        if isinstance(error, RateLimitError):
            return True

        # Retry on connection/timeout errors
        error_name = type(error).__name__
        if any(name in error_name for name in ("Timeout", "Connection", "Network")):
            return True

        return False

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay with jitter."""
        base = self.config.retry_backoff * attempt
        jitter = self.config.retry_jitter * (0.5 - (hash(str(attempt)) % 100) / 100.0)
        return max(0.0, base + jitter)

    def fetch_with_retry(self, url: str, **kwargs: Any) -> EngineResult:
        """
        Fetch with automatic retry logic.

        This is the main entry point that scrapers should use.
        """
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt <= self.config.max_retries:
            if self.config.rate_limiter:
                self.config.rate_limiter.wait()

            try:
                return self.fetch(url, **kwargs)
            except RateLimitError as exc:
                last_error = exc
                safe_log(
                    log,
                    "warning",
                    "Rate limit detected",
                    extra={"url": url, "attempt": attempt},
                )
                # Longer backoff for rate limits
                if attempt < self.config.max_retries:
                    delay = self._calculate_backoff(attempt) * 2
                    time.sleep(delay)
            except Exception as exc:
                last_error = exc
                if not self._should_retry(attempt, exc):
                    break

                safe_log(
                    log,
                    "warning",
                    "Fetch failed, retrying",
                    extra={
                        "url": url,
                        "attempt": attempt,
                        "error": type(exc).__name__,
                    },
                )

            attempt += 1
            if attempt <= self.config.max_retries:
                delay = self._calculate_backoff(attempt)
                time.sleep(delay)

        # All retries exhausted
        raise EngineError(
            f"Failed to fetch {url} after {self.config.max_retries} retries",
            url=url,
            retries_exhausted=True,
        ) from last_error

    def is_closed(self) -> bool:
        """Check if engine has been closed."""
        return self._closed

    def _mark_closed(self) -> None:
        """Mark engine as closed."""
        self._closed = True


__all__ = ["BaseEngine", "EngineConfig", "EngineResult", "EngineError", "RateLimitError"]

