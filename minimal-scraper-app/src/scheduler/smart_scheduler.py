# src/scheduler/smart_scheduler.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from src.common.logging_utils import get_logger

log = get_logger("smart-scheduler")

@dataclass
class SourceScheduleConfig:
    source: str
    min_interval_minutes: int = 30
    max_interval_minutes: int = 24 * 60
    default_interval_minutes: int = 60
    high_change_interval_minutes: int = 15
    low_change_interval_minutes: int = 6 * 60
    max_fail_streak_before_backoff: int = 3

@dataclass
class SourceMetricsSnapshot:
    source: str
    last_run_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_change_ratio: float
    consecutive_failures: int
    budget_exhausted: bool = False

def _clamp_interval(config: SourceScheduleConfig, minutes: int) -> int:
    return max(config.min_interval_minutes, min(config.max_interval_minutes, minutes))

def compute_next_run_time(
    now: datetime,
    config: SourceScheduleConfig,
    metrics: SourceMetricsSnapshot,
) -> Optional[datetime]:
    if metrics.budget_exhausted:
        log.warning("Budget exhausted for %s, not scheduling new run.", config.source)
        return None
    interval = config.default_interval_minutes
    if metrics.consecutive_failures >= config.max_fail_streak_before_backoff:
        backoff_factor = min(4, metrics.consecutive_failures - config.max_fail_streak_before_backoff + 1)
        interval *= backoff_factor
        log.info(
            "Applying backoff for %s (failures=%d, factor=%d)",
            config.source,
            metrics.consecutive_failures,
            backoff_factor,
        )
    if metrics.last_change_ratio >= 0.5:
        interval = min(interval, config.high_change_interval_minutes)
    elif metrics.last_change_ratio <= 0.05:
        interval = max(interval, config.low_change_interval_minutes)
    interval = _clamp_interval(config, interval)
    base = metrics.last_run_at or now
    next_run = base + timedelta(minutes=interval)
    log.debug(
        "Next run for %s at %s (interval=%d mins, change_ratio=%.3f, failures=%d)",
        config.source,
        next_run,
        interval,
        metrics.last_change_ratio,
        metrics.consecutive_failures,
    )
    return next_run
