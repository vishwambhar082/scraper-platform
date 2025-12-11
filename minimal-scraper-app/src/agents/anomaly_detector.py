# src/agents/anomaly_detector.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class Anomaly:
    index: int
    value: float
    z_score: float


def detect_zscore_anomalies(values: Sequence[float], threshold: float = 3.0) -> List[Anomaly]:
    if not values:
        return []
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
    std = var ** 0.5
    if std == 0:
        return []

    anomalies: List[Anomaly] = []
    for idx, v in enumerate(values):
        z = (v - mean) / std
        if abs(z) >= threshold:
            anomalies.append(Anomaly(index=idx, value=v, z_score=z))
    return anomalies


__all__ = ["Anomaly", "detect_zscore_anomalies"]
