"""
Adaptive Rate Limiter

Automatically adjusts request rate based on 429 responses and server feedback.
Implements token bucket algorithm with exponential backoff on rate limiting.

Author: Scraper Platform Team
Date: 2025-12-13
"""

import time
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.common.logging_utils import get_logger

log = get_logger("adaptive_rate_limiter")


@dataclass
class RateLimitStats:
    """Statistics for rate limiting."""

    total_requests: int = 0
    rate_limited_requests: int = 0
    current_qps: float = 0.0
    max_qps: float = 0.0
    min_qps: float = 0.0
    backoff_count: int = 0
    last_rate_limit: Optional[datetime] = None

    def to_dict(self):
        return {
            "total_requests": self.total_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "current_qps": self.current_qps,
            "max_qps": self.max_qps,
            "min_qps": self.min_qps,
            "backoff_count": self.backoff_count,
            "last_rate_limit": self.last_rate_limit.isoformat() if self.last_rate_limit else None,
        }


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter with automatic backoff on 429 errors.

    Features:
    - Token bucket algorithm for smooth rate limiting
    - Automatic backoff on rate limit detection
    - Gradual recovery after backoff
    - Thread-safe operations
    - Statistics tracking
    - Configurable min/max QPS bounds
    """

    def __init__(
        self,
        initial_qps: float = 10.0,
        min_qps: float = 0.1,
        max_qps: float = 100.0,
        backoff_factor: float = 0.5,
        recovery_factor: float = 1.1,
        recovery_interval_seconds: float = 60.0,
    ):
        """Initialize adaptive rate limiter.

        Args:
            initial_qps: Initial queries per second
            min_qps: Minimum allowed QPS
            max_qps: Maximum allowed QPS
            backoff_factor: Factor to reduce QPS on rate limit (0.0-1.0)
            recovery_factor: Factor to increase QPS during recovery (>1.0)
            recovery_interval_seconds: Time between recovery attempts
        """
        self.initial_qps = initial_qps
        self.min_qps = min_qps
        self.max_qps = max_qps
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self.recovery_interval_seconds = recovery_interval_seconds

        # Current state
        self.current_qps = initial_qps
        self.tokens = initial_qps
        self.last_refill = time.time()
        self.last_recovery = time.time()
        self.in_backoff = False

        # Statistics
        self.stats = RateLimitStats(
            current_qps=initial_qps,
            max_qps=max_qps,
            min_qps=min_qps,
        )

        # Thread safety
        self._lock = threading.RLock()

        log.info(
            f"Initialized adaptive rate limiter: "
            f"initial_qps={initial_qps}, min={min_qps}, max={max_qps}"
        )

    def wait_if_needed(self) -> float:
        """Wait if necessary to respect rate limit.

        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        with self._lock:
            # Refill tokens
            now = time.time()
            elapsed = now - self.last_refill
            self.last_refill = now

            # Add tokens based on current QPS
            tokens_to_add = self.current_qps * elapsed
            self.tokens = min(self.tokens + tokens_to_add, self.current_qps)

            # Check if we need to wait
            if self.tokens < 1.0:
                # Calculate wait time
                wait_time = (1.0 - self.tokens) / self.current_qps
                log.debug(f"Rate limit wait: {wait_time:.3f}s")

                # Release lock during sleep
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()

                # Refill after wait
                self.tokens = 1.0
                self.last_refill = time.time()

                return wait_time

            # Consume token
            self.tokens -= 1.0
            self.stats.total_requests += 1

            # Try recovery if in backoff
            if self.in_backoff and (now - self.last_recovery) > self.recovery_interval_seconds:
                self._attempt_recovery()

            return 0.0

    def report_rate_limit(self) -> None:
        """Report that a rate limit (429) was encountered.

        This triggers automatic backoff.
        """
        with self._lock:
            self.stats.rate_limited_requests += 1
            self.stats.last_rate_limit = datetime.now()
            self.stats.backoff_count += 1

            # Calculate new QPS with backoff
            old_qps = self.current_qps
            self.current_qps = max(
                self.min_qps,
                self.current_qps * self.backoff_factor
            )

            self.in_backoff = True
            self.last_recovery = time.time()

            log.warning(
                f"Rate limit detected! Backing off: {old_qps:.2f} -> {self.current_qps:.2f} QPS"
            )

            # Reset tokens to prevent burst
            self.tokens = min(self.tokens, self.current_qps / 2)

    def report_success(self) -> None:
        """Report successful request (no rate limiting).

        This helps track when it's safe to increase rate.
        """
        # Success doesn't immediately trigger recovery,
        # but is tracked for statistics
        pass

    def _attempt_recovery(self) -> None:
        """Attempt to recover QPS after backoff period.

        This gradually increases QPS back towards max_qps.
        """
        old_qps = self.current_qps
        self.current_qps = min(
            self.max_qps,
            self.current_qps * self.recovery_factor
        )

        self.last_recovery = time.time()

        # If we've recovered fully, exit backoff mode
        if self.current_qps >= self.max_qps:
            self.in_backoff = False

        log.info(
            f"Rate limit recovery: {old_qps:.2f} -> {self.current_qps:.2f} QPS "
            f"(backoff={'active' if self.in_backoff else 'cleared'})"
        )

    def set_qps(self, qps: float) -> None:
        """Manually set QPS.

        Args:
            qps: Queries per second
        """
        with self._lock:
            qps = max(self.min_qps, min(self.max_qps, qps))
            old_qps = self.current_qps
            self.current_qps = qps
            self.stats.current_qps = qps

            log.info(f"QPS manually set: {old_qps:.2f} -> {qps:.2f}")

    def get_stats(self) -> RateLimitStats:
        """Get current rate limiting statistics.

        Returns:
            RateLimitStats
        """
        with self._lock:
            self.stats.current_qps = self.current_qps
            return self.stats

    def reset(self) -> None:
        """Reset rate limiter to initial state."""
        with self._lock:
            self.current_qps = self.initial_qps
            self.tokens = self.initial_qps
            self.last_refill = time.time()
            self.last_recovery = time.time()
            self.in_backoff = False

            self.stats = RateLimitStats(
                current_qps=self.initial_qps,
                max_qps=self.max_qps,
                min_qps=self.min_qps,
            )

            log.info("Rate limiter reset to initial state")


class PerDomainRateLimiter:
    """
    Manage separate rate limiters for different domains.

    This allows different rate limits for different websites.
    """

    def __init__(
        self,
        default_qps: float = 10.0,
        min_qps: float = 0.1,
        max_qps: float = 100.0,
    ):
        """Initialize per-domain rate limiter.

        Args:
            default_qps: Default QPS for new domains
            min_qps: Minimum QPS
            max_qps: Maximum QPS
        """
        self.default_qps = default_qps
        self.min_qps = min_qps
        self.max_qps = max_qps

        self._limiters: dict[str, AdaptiveRateLimiter] = {}
        self._lock = threading.RLock()

    def get_limiter(self, domain: str) -> AdaptiveRateLimiter:
        """Get rate limiter for specific domain.

        Args:
            domain: Domain name

        Returns:
            AdaptiveRateLimiter for the domain
        """
        with self._lock:
            if domain not in self._limiters:
                self._limiters[domain] = AdaptiveRateLimiter(
                    initial_qps=self.default_qps,
                    min_qps=self.min_qps,
                    max_qps=self.max_qps,
                )
                log.info(f"Created rate limiter for domain: {domain}")

            return self._limiters[domain]

    def wait_for_domain(self, domain: str) -> float:
        """Wait if needed for specific domain.

        Args:
            domain: Domain name

        Returns:
            Wait time in seconds
        """
        limiter = self.get_limiter(domain)
        return limiter.wait_if_needed()

    def report_rate_limit(self, domain: str) -> None:
        """Report rate limit for specific domain.

        Args:
            domain: Domain name
        """
        limiter = self.get_limiter(domain)
        limiter.report_rate_limit()

    def get_all_stats(self) -> dict[str, RateLimitStats]:
        """Get statistics for all domains.

        Returns:
            Dictionary of domain -> RateLimitStats
        """
        with self._lock:
            return {
                domain: limiter.get_stats()
                for domain, limiter in self._limiters.items()
            }
