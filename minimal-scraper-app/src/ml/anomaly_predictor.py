"""
Simple anomaly detector based on rolling z-score.
"""
from __future__ import annotations

import statistics
from typing import Iterable, List


class AnomalyPredictor:
    def detect(self, values: Iterable[float], threshold: float = 3.0) -> List[int]:
        data = list(values)
        if len(data) < 2:
            return []
        mean = statistics.mean(data)
        stdev = statistics.stdev(data)
        if stdev == 0:
            return []
        return [idx for idx, value in enumerate(data) if abs(value - mean) / stdev >= threshold]

