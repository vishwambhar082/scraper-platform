import json
import logging
import os
import re
import sys
from typing import Any, Dict, Mapping, Optional


_DEFAULT_LEVEL = os.getenv("SCRAPER_LOG_LEVEL", "INFO").upper()


class JsonLogFormatter(logging.Formatter):
    """
    Serialize log records as JSON for easier ingestion by Loki/ELK/etc.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Format timestamp with microseconds
        import datetime
        # Use UTC time
        ct = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)
        # Format with microseconds
        timestamp = ct.strftime("%Y-%m-%dT%H:%M:%S") + f".{ct.microsecond:06d}Z"
        
        base: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach standard attributes if present
        for attr in ("filename", "lineno", "funcName"):
            base[attr] = getattr(record, attr, None)

        # Attach extra fields from `extra=...`
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            base.update(record.extra)

        # Common contextual fields that we may pass via `extra`
        for key in ("run_id", "source", "step", "proxy_id", "account_id"):
            value = getattr(record, key, None)
            if value is not None:
                base[key] = value

        return json.dumps(base, ensure_ascii=False)


_ROOT_HANDLER: Optional[logging.Handler] = None


def _configure_root_logger() -> None:
    global _ROOT_HANDLER
    if _ROOT_HANDLER is not None:
        return

    root = logging.getLogger()
    root.setLevel(_DEFAULT_LEVEL)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root.addHandler(handler)
    _ROOT_HANDLER = handler


def get_logger(name: str) -> logging.Logger:
    """
    Return a module-level logger with JSON formatting and shared configuration.

    Usage:
        log = get_logger(__name__)
        log.info("Starting scrape", extra={"source": "alfabeta", "run_id": run_id})
    """
    _configure_root_logger()
    return logging.getLogger(name)


def with_context(logger: logging.Logger, **kwargs: Any) -> logging.LoggerAdapter:
    """
    Wrap a logger with additional contextual fields.

    Example:
        log = with_context(get_logger(__name__), source="alfabeta", run_id=run_id)
        log.info("Step started")
    """
    return logging.LoggerAdapter(logger, extra=kwargs)


SENSITIVE_KEYS = {"password", "passwd", "token", "api_key", "secret", "proxy", "proxy_url"}


SENSITIVE_PATTERNS = [
    re.compile(r"(token|apikey|api_key|password|passwd|secret)=[^&\s]+", re.I),
    re.compile(r"https?:\/\/[^\/]+:[^@]+@"),  # redact creds in URLs
]


def safe_message(msg: str) -> str:
    clean = msg
    for pattern in SENSITIVE_PATTERNS:
        clean = pattern.sub("***redacted***", clean)
    return clean


def sanitize_for_log(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a shallow copy of data with sensitive fields redacted.
    """
    sanitized: Dict[str, Any] = {}
    for k, v in data.items():
        lk = k.lower()
        if lk in SENSITIVE_KEYS:
            sanitized[k] = "***redacted***"
        elif isinstance(v, str):
            sanitized[k] = safe_message(v)
        else:
            sanitized[k] = v
    return sanitized


def safe_log(logger, level: str, msg: str, extra: dict | None = None):
    clean_msg = safe_message(msg)
    clean_extra = sanitize_for_log(extra or {})
    getattr(logger, level)(clean_msg, extra=clean_extra)
