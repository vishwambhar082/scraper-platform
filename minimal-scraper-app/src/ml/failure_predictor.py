"""
Heuristic failure predictor that scores runs based on metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class FailurePrediction:
    probability: float
    reasons: Dict[str, float]


class FailurePredictor:
    def predict(self, features: Dict[str, float]) -> FailurePrediction:
        score = 0.0
        reasons: Dict[str, float] = {}
        if (features.get("error_rate") or 0) > 0.2:
            reasons["error_rate"] = features["error_rate"]
            score += 0.4
        if (features.get("latency_p95") or 0) > 5.0:
            reasons["latency_p95"] = features["latency_p95"]
            score += 0.3
        if (features.get("proxy_failures") or 0) > 5:
            reasons["proxy_failures"] = features["proxy_failures"]
            score += 0.3
        return FailurePrediction(probability=min(score, 0.99), reasons=reasons)

