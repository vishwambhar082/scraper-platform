# src/agents/drift_analyzer.py

from __future__ import annotations

from dataclasses import dataclass

from src.observability.drift_monitor import DriftStatus, simple_drift_check


@dataclass
class DriftDecision:
    status: DriftStatus
    action: str  # "noop" | "investigate" | "halt"


def analyze_volume_drift(baseline_rows: int, current_rows: int) -> DriftDecision:
    status = simple_drift_check(baseline_rows, current_rows)
    if not status.has_drift:
        action = "noop"
    elif abs(status.volume.pct_change) < 100:
        action = "investigate"
    else:
        action = "halt"
    return DriftDecision(status=status, action=action)


__all__ = ["DriftDecision", "analyze_volume_drift"]
