# src/observability/volume_drift.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VolumeDriftResult:
    baseline_rows: int
    current_rows: int
    delta: int
    pct_change: float


def compute_volume_drift(baseline_rows: int, current_rows: int) -> VolumeDriftResult:
    delta = current_rows - baseline_rows
    pct = 0.0
    if baseline_rows > 0:
        pct = (delta / baseline_rows) * 100.0
    return VolumeDriftResult(
        baseline_rows=baseline_rows,
        current_rows=current_rows,
        delta=delta,
        pct_change=pct,
    )


__all__ = ["VolumeDriftResult", "compute_volume_drift"]
