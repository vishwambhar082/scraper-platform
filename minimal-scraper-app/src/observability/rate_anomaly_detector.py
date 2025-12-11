# src/observability/rate_anomaly_detector.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RatePoint:
    ts: float
    value: float


def is_spike(points: List[RatePoint], factor: float = 3.0) -> bool:
    if len(points) < 5:
        return False
    *history, last = points
    vals = sorted(p.value for p in history)
    mid = len(vals) // 2
    if len(vals) % 2 == 1:
        median = vals[mid]
    else:
        median = (vals[mid - 1] + vals[mid]) / 2.0
    if median <= 0:
        return False
    return last.value > factor * median


def detect_rate_anomaly(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight anomaly detector based on recent rate history."""

    raw_points = signal.get("points") or []
    points: List[RatePoint] = []
    for raw in raw_points:
        try:
            points.append(RatePoint(ts=float(raw["ts"]), value=float(raw["value"])))
        except (KeyError, TypeError, ValueError):
            continue

    anomalous = is_spike(points)
    return {"is_anomalous": anomalous, "points": points}
