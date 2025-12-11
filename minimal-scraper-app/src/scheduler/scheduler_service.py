# src/scheduler/scheduler_service.py
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from src.common.logging_utils import get_logger
from src.scheduler.smart_scheduler import SourceScheduleConfig, SourceMetricsSnapshot, compute_next_run_time

log = get_logger("scheduler-service")


def compute_schedules(
    now: datetime,
    configs: Iterable[SourceScheduleConfig],
    metrics: Iterable[SourceMetricsSnapshot],
) -> List[tuple[str, Optional[datetime]]]:
    metrics_by_source = {m.source: m for m in metrics}
    results: List[tuple[str, Optional[datetime]]] = []
    for cfg in configs:
        m = metrics_by_source.get(cfg.source)
        if not m:
            log.warning("No metrics for source %s; skipping", cfg.source)
            continue
        nxt = compute_next_run_time(now, cfg, m)
        results.append((cfg.source, nxt))
    return results
