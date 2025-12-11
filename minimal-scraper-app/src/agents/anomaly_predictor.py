# file: src/agents/anomaly_predictor.py
"""
Forecast / predict anomalies using recent metrics.

This is kept as a thin façade over observability.rate_anomaly_detector.
"""

from __future__ import annotations

from typing import Any, Dict

from src.observability import rate_anomaly_detector


def predict_anomalies(signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delegate to the rate_anomaly_detector for now.
    """
    return rate_anomaly_detector.detect_rate_anomaly(signal)
