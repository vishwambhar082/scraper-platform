from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from src.common.logging_utils import get_logger, with_context


log = get_logger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def emit_alert(
    code: str,
    message: str,
    *,
    severity: AlertSeverity = AlertSeverity.WARNING,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit a structured alert.

    For now this is implemented as a structured log entry. In future this can be
    wired to Slack, PagerDuty, Alertmanager, etc. without changing callers.

    Args:
        code: Stable identifier, e.g. "PCID_MATCH_RATE_DROP"
        message: Human-readable description.
        severity: INFO/WARNING/CRITICAL.
        context: Extra fields (source, run_id, metric values, thresholds, etc.).
    """

    extra = {"alert_code": code, "alert_severity": severity.value}
    if context:
        extra.update(context)

    ctx_log = with_context(log, **extra)

    if severity == AlertSeverity.CRITICAL:
        ctx_log.error(message)
    elif severity == AlertSeverity.WARNING:
        ctx_log.warning(message)
    else:
        ctx_log.info(message)
