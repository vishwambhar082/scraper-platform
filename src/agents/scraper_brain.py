# src/agents/scraper_brain.py

from __future__ import annotations

from dataclasses import dataclass

from src.agents.anomaly_detector import detect_zscore_anomalies
from src.agents.drift_analyzer import DriftDecision, analyze_volume_drift
from src.common.logging_utils import get_logger

log = get_logger("scraper-brain")


@dataclass
class ScraperAssessment:
    source: str
    drift_decision: DriftDecision
    has_volume_anomaly: bool


def assess_source_health(source: str, baseline_rows: int, current_rows: int) -> ScraperAssessment:
    drift_decision = analyze_volume_drift(baseline_rows, current_rows)
    anomalies = detect_zscore_anomalies([baseline_rows, current_rows], threshold=2.5)
    has_anom = len(anomalies) > 0
    log.info(
        "Source %s assessment: drift_action=%s, has_volume_anomaly=%s",
        source,
        drift_decision.action,
        has_anom,
    )
    return ScraperAssessment(
        source=source,
        drift_decision=drift_decision,
        has_volume_anomaly=has_anom,
    )


__all__ = ["ScraperAssessment", "assess_source_health"]
