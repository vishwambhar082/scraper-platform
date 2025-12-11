# src/observability/drift_monitor.py

from __future__ import annotations

from dataclasses import dataclass

from src.common.logging_utils import get_logger
from src.observability.alerts import AlertSeverity, emit_alert
from src.observability.volume_drift import compute_volume_drift, VolumeDriftResult


log = get_logger(__name__)


@dataclass
class DriftStatus:
    has_drift: bool
    volume: VolumeDriftResult


def simple_drift_check(baseline_rows: int, current_rows: int, pct_threshold: float = 50.0) -> DriftStatus:
    vol = compute_volume_drift(baseline_rows, current_rows)
    has_drift = abs(vol.pct_change) >= pct_threshold

    if has_drift:
        context = {
            "baseline_rows": baseline_rows,
            "current_rows": current_rows,
            "delta": vol.delta,
            "pct_change": vol.pct_change,
            "pct_threshold": pct_threshold,
        }
        log.warning("Volume drift detected", extra={"drift": context})
        emit_alert(
            code="VOLUME_DRIFT",
            message=(
                f"Volume drift detected: pct_change={vol.pct_change:.2f}% "
                f"(threshold={pct_threshold:.2f}%), baseline={baseline_rows}, current={current_rows}"
            ),
            severity=AlertSeverity.WARNING,
            context=context,
        )

    return DriftStatus(has_drift=has_drift, volume=vol)


__all__ = ["DriftStatus", "simple_drift_check"]
