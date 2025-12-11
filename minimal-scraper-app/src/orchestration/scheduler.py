"""
High-level scheduler facade that leverages the smart scheduler heuristics.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from src.scheduler.smart_scheduler import (
    SourceMetricsSnapshot,
    SourceScheduleConfig,
    compute_next_run_time,
)


class OrchestrationScheduler:
    def __init__(self, configs: Iterable[SourceScheduleConfig]) -> None:
        self._config_index = {cfg.source: cfg for cfg in configs}

    def plan_next_run(
        self,
        source: str,
        metrics: SourceMetricsSnapshot,
        now: Optional[datetime] = None,
    ) -> Optional[datetime]:
        config = self._config_index.get(source)
        if not config:
            raise KeyError(f"Unknown source config: {source}")
        return compute_next_run_time(now or datetime.utcnow(), config, metrics)

    def upcoming_runs(
        self, snapshots: Iterable[SourceMetricsSnapshot], now: Optional[datetime] = None
    ) -> List[tuple[str, Optional[datetime]]]:
        plan = []
        for snapshot in snapshots:
            plan.append((snapshot.source, self.plan_next_run(snapshot.source, snapshot, now)))
        return plan

