# src/observability/logging.py

from typing import Any, Dict
from datetime import datetime

from src.common.logging_utils import get_logger

log = get_logger("observability")


def log_event(event_type: str, source: str | None = None, **fields: Any) -> None:
    """
    Log a structured observability event.
    """
    record: Dict[str, Any] = {
        "ts": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "source": source,
        "fields": fields,
    }
    log.info("OBS_EVENT %s", record)


__all__ = ["log_event"]
