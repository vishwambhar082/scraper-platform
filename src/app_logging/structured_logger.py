"""
Structured JSON logging using structlog with high-performance optimizations.

This module provides:
- JSON-formatted structured logging
- Thread-safe context binding
- Sensitive data masking
- Stack trace formatting
- ISO 8601 timestamp formatting
- File rotation support
- Console and file outputs
- Integration with existing unified_logger.py
- Performance optimizations for high-volume logging

Features:
- Automatic context injection (run_id, source, step_id)
- Sensitive data redaction (passwords, tokens, cookies)
- Efficient log processors with caching
- Minimal overhead for production use
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Pattern

import structlog
from structlog.types import EventDict, WrappedLogger


# ============================================================================
# Configuration Constants
# ============================================================================

DEFAULT_LOG_LEVEL = os.getenv("SCRAPER_LOG_LEVEL", "INFO").upper()
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_JSON_LOG_FILE = "scraper_structured.jsonl"
DEFAULT_MAX_BYTES = 100 * 1024 * 1024  # 100 MB
DEFAULT_BACKUP_COUNT = 10

# Sensitive field patterns for masking
SENSITIVE_FIELD_NAMES = {
    "password",
    "passwd",
    "pwd",
    "token",
    "api_key",
    "apikey",
    "secret",
    "api_secret",
    "auth",
    "authorization",
    "cookie",
    "cookies",
    "session",
    "session_id",
    "access_token",
    "refresh_token",
    "bearer",
    "credentials",
    "credential",
    "private_key",
    "encryption_key",
    "fernet_key",
}

# Compiled regex patterns for sensitive data in strings
SENSITIVE_VALUE_PATTERNS: List[Pattern] = [
    # Tokens and API keys in format: key=value or key:value
    re.compile(r"(token|apikey|api_key|password|passwd|secret|auth)[:=][^\s&]+", re.IGNORECASE),
    # Credentials in URLs (http://user:pass@host)
    re.compile(r"https?://[^/\s]+:[^@\s]+@", re.IGNORECASE),
    # Bearer tokens
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    # JWT tokens (base64.base64.base64)
    re.compile(r"eyJ[A-Za-z0-9\-._~+/]+=*\.eyJ[A-Za-z0-9\-._~+/]+=*\.[A-Za-z0-9\-._~+/]+=*"),
    # Cookie values
    re.compile(r"(Cookie|Set-Cookie):\s*[^\n]+", re.IGNORECASE),
]

REDACTED_TEXT = "***REDACTED***"


# ============================================================================
# Processors
# ============================================================================

def add_timestamp(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add ISO 8601 formatted timestamp with microseconds and UTC timezone.

    Format: 2025-12-13T19:45:23.123456Z
    """
    import datetime

    timestamp = datetime.datetime.now(datetime.timezone.utc)
    event_dict["timestamp"] = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return event_dict


def add_log_level(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add normalized log level to event dict.

    Converts method name (info, warning, etc.) to uppercase level name.
    """
    # Map structlog method names to standard log levels
    level_map = {
        "debug": "DEBUG",
        "info": "INFO",
        "warning": "WARNING",
        "warn": "WARNING",
        "error": "ERROR",
        "critical": "CRITICAL",
        "exception": "ERROR",
    }

    event_dict["level"] = level_map.get(method_name, "INFO")
    return event_dict


def add_logger_name(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add logger name from the wrapped logger.
    """
    if hasattr(logger, "name"):
        event_dict["logger"] = logger.name
    return event_dict


def format_exc_info(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Format exception information into structured data.

    Extracts exception type, message, and formatted traceback.
    """
    exc_info = event_dict.pop("exc_info", None)

    if exc_info:
        if exc_info is True:
            exc_info = sys.exc_info()

        if exc_info and exc_info != (None, None, None):
            exc_type, exc_value, exc_tb = exc_info

            event_dict["exception"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_value) if exc_value else "",
                "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                if exc_tb
                else "",
            }

    return event_dict


def mask_sensitive_string(value: str) -> str:
    """
    Mask sensitive data in a string value using regex patterns.

    Args:
        value: String to check and mask

    Returns:
        Masked string with sensitive data replaced
    """
    if not isinstance(value, str):
        return value

    masked = value
    for pattern in SENSITIVE_VALUE_PATTERNS:
        masked = pattern.sub(REDACTED_TEXT, masked)

    return masked


def mask_sensitive_data(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Mask sensitive data in log events.

    Checks both field names and values for sensitive information.
    Recursively processes nested dictionaries.
    """
    def _mask_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask sensitive fields in a dictionary."""
        masked = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Check if field name is sensitive
            if any(sensitive_key in key_lower for sensitive_key in SENSITIVE_FIELD_NAMES):
                masked[key] = REDACTED_TEXT
            elif isinstance(value, dict):
                # Recursively mask nested dicts
                masked[key] = _mask_dict(value)
            elif isinstance(value, list):
                # Process list items
                masked[key] = [
                    _mask_dict(item) if isinstance(item, dict) else mask_sensitive_string(str(item))
                    for item in value
                ]
            elif isinstance(value, str):
                # Mask sensitive patterns in string values
                masked[key] = mask_sensitive_string(value)
            else:
                masked[key] = value

        return masked

    # Mask the event message
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["event"] = mask_sensitive_string(event_dict["event"])

    # Mask all other fields
    masked_event = _mask_dict(event_dict)

    return masked_event


def inject_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Inject context variables from thread-local storage.

    Automatically adds run_id, source, step_id, and other context
    from the log_context module if available.
    """
    try:
        from src.app_logging.log_context import get_context

        context = get_context()
        if context:
            # Only add context items that aren't already in event_dict
            for key, value in context.items():
                if key not in event_dict:
                    event_dict[key] = value
    except ImportError:
        # log_context module not available yet
        pass

    return event_dict


def add_caller_info(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add caller information (filename, line number, function name).

    Note: This adds overhead and should be disabled in production
    if performance is critical.
    """
    # Only add if not already present (from standard library integration)
    if "filename" not in event_dict:
        import inspect

        frame = inspect.currentframe()
        if frame:
            # Walk up the stack to find the actual caller (skip structlog internals)
            caller_frame = frame
            while caller_frame:
                caller_frame = caller_frame.f_back
                if caller_frame and not (
                    "structlog" in caller_frame.f_code.co_filename
                    or "logging" in caller_frame.f_code.co_filename
                ):
                    event_dict["filename"] = Path(caller_frame.f_code.co_filename).name
                    event_dict["lineno"] = caller_frame.f_lineno
                    event_dict["funcName"] = caller_frame.f_code.co_name
                    break

    return event_dict


def drop_color_message_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Remove the color_message key added by ConsoleRenderer in production.
    """
    event_dict.pop("color_message", None)
    return event_dict


# ============================================================================
# Renderer/Serializer
# ============================================================================

def json_renderer(logger: WrappedLogger, name: str, event_dict: EventDict) -> str:
    """
    Render event dict as a JSON string with newline.

    Optimized for performance with ensure_ascii=False and separators.
    """
    import json

    return json.dumps(event_dict, ensure_ascii=False, separators=(",", ":"), default=str)


# ============================================================================
# Logger Configuration
# ============================================================================

def configure_structured_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[Path] = None,
    json_log_file: Optional[str] = None,
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_caller_info: bool = False,
    cache_logger_on_first_use: bool = True,
) -> None:
    """
    Configure structured logging with JSON output and file rotation.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        json_log_file: Name of JSON log file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        enable_console: Enable console output (JSON to stdout)
        enable_file: Enable file output with rotation
        enable_caller_info: Add caller info (adds overhead, disable for production)
        cache_logger_on_first_use: Cache logger configuration (performance optimization)

    Example:
        configure_structured_logging(
            log_level="INFO",
            log_dir=Path("logs"),
            enable_console=True,
            enable_file=True,
        )
    """
    # Use defaults
    log_level = log_level or DEFAULT_LOG_LEVEL
    log_dir = log_dir or DEFAULT_LOG_DIR
    json_log_file = json_log_file or DEFAULT_JSON_LOG_FILE
    max_bytes = max_bytes or DEFAULT_MAX_BYTES
    backup_count = backup_count or DEFAULT_BACKUP_COUNT

    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    handlers: List[logging.Handler] = []

    # Console handler (JSON to stdout)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        handlers.append(console_handler)

    # File handler with rotation (JSON to file)
    if enable_file:
        log_file_path = log_dir / json_log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)

    # Build processor chain
    processors: List[Callable] = [
        # Add context variables first
        inject_context,
        # Add log level
        add_log_level,
        # Add logger name
        add_logger_name,
        # Add timestamp
        add_timestamp,
        # Format exception info
        format_exc_info,
        # Mask sensitive data (IMPORTANT: Do this before serialization)
        mask_sensitive_data,
        # Add caller info if enabled (adds overhead)
    ]

    if enable_caller_info:
        processors.append(add_caller_info)

    # Add final processor based on output type
    processors.extend([
        # Drop color message key if present
        drop_color_message_key,
        # Wrap logger for stdlib integration
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ])

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=cache_logger_on_first_use,
    )

    # Configure structlog's ProcessorFormatter for stdlib integration
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=json_renderer,
        foreign_pre_chain=[
            add_log_level,
            add_timestamp,
        ],
    )

    # Apply formatter to all handlers
    for handler in handlers:
        handler.setFormatter(formatter)


def get_structured_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (defaults to caller's module name)

    Returns:
        Configured structlog BoundLogger instance

    Example:
        log = get_structured_logger(__name__)
        log.info("scrape_started", source="alfabeta", run_id="12345")
    """
    if name is None:
        # Get caller's module name
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_module = frame.f_back.f_globals.get("__name__", "root")
            name = caller_module
        else:
            name = "root"

    return structlog.get_logger(name)


def bind_contextvars(**kwargs: Any) -> None:
    """
    Bind context variables that will be automatically included in all log entries.

    This is a convenience wrapper around structlog.contextvars.bind_contextvars.

    Args:
        **kwargs: Context variables to bind

    Example:
        bind_contextvars(run_id="12345", source="alfabeta")
        log.info("step_started")  # Automatically includes run_id and source
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_contextvars(*keys: str) -> None:
    """
    Unbind specific context variables.

    Args:
        *keys: Keys to unbind

    Example:
        unbind_contextvars("run_id", "source")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_contextvars() -> None:
    """
    Clear all bound context variables.

    Example:
        clear_contextvars()
    """
    structlog.contextvars.clear_contextvars()


# ============================================================================
# Integration with Unified Logger
# ============================================================================

class StructuredUnifiedLogger:
    """
    Adapter to integrate structured logging with the existing UnifiedLogger.

    This class provides a bridge between the new structured logging system
    and the existing unified_logger.py implementation.
    """

    def __init__(
        self,
        logger: Optional[structlog.BoundLogger] = None,
        unified_logger: Optional[Any] = None,
    ) -> None:
        """
        Initialize the structured unified logger.

        Args:
            logger: Structlog logger instance (creates one if None)
            unified_logger: UnifiedLogger instance for backwards compatibility
        """
        self.logger = logger or get_structured_logger("unified-logger")
        self.unified_logger = unified_logger

    def log(
        self,
        level: str,
        message: str,
        logger: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
        source: Optional[str] = None,
        run_id: Optional[str] = None,
        step_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log a structured message with optional context.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            logger: Logger name override
            job_id: Job ID
            task_id: Task ID
            source: Source name
            run_id: Run ID
            step_id: Step ID
            metadata: Additional metadata
            **kwargs: Additional context to include
        """
        # Build context
        context = {}

        if logger:
            context["logger_name"] = logger
        if job_id:
            context["job_id"] = job_id
        if task_id:
            context["task_id"] = task_id
        if source:
            context["source"] = source
        if run_id:
            context["run_id"] = run_id
        if step_id:
            context["step_id"] = step_id
        if metadata:
            context.update(metadata)

        context.update(kwargs)

        # Get the appropriate log method
        log_method = getattr(self.logger, level.lower(), self.logger.info)

        # Log the message
        log_method(message, **context)

        # Also log to unified logger if available (for backwards compatibility)
        if self.unified_logger:
            try:
                self.unified_logger.log(
                    level=level,
                    message=message,
                    logger=logger,
                    job_id=job_id,
                    task_id=task_id,
                    source=source,
                    run_id=run_id,
                    metadata=metadata,
                )
            except Exception as e:
                # Don't fail if unified logger has issues
                self.logger.warning("unified_logger_error", error=str(e))

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self.log("INFO", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self.log("DEBUG", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self.log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self.log("CRITICAL", message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log an exception with traceback."""
        kwargs["exc_info"] = True
        self.log("ERROR", message, **kwargs)


# ============================================================================
# Global Instance
# ============================================================================

_global_structured_logger: Optional[StructuredUnifiedLogger] = None


def get_global_structured_logger() -> StructuredUnifiedLogger:
    """
    Get the global structured logger instance.

    Returns:
        Global StructuredUnifiedLogger instance

    Example:
        logger = get_global_structured_logger()
        logger.info("Application started", version="5.0")
    """
    global _global_structured_logger

    if _global_structured_logger is None:
        # Try to import and use existing unified logger
        try:
            from src.app_logging.unified_logger import get_unified_logger

            unified_logger = get_unified_logger()
            _global_structured_logger = StructuredUnifiedLogger(
                unified_logger=unified_logger
            )
        except ImportError:
            # Unified logger not available
            _global_structured_logger = StructuredUnifiedLogger()

    return _global_structured_logger


# ============================================================================
# Convenience Functions
# ============================================================================

def setup_production_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    enable_console: bool = True,
) -> None:
    """
    Setup production-optimized structured logging.

    Disables caller info for performance, enables file rotation,
    and configures appropriate log levels.

    Args:
        log_level: Log level for production
        log_dir: Log directory
        enable_console: Enable console output

    Example:
        setup_production_logging(log_level="INFO", log_dir=Path("/var/log/scraper"))
    """
    configure_structured_logging(
        log_level=log_level,
        log_dir=log_dir,
        enable_console=enable_console,
        enable_file=True,
        enable_caller_info=False,  # Disable for performance
        cache_logger_on_first_use=True,  # Enable caching for performance
    )


def setup_development_logging(
    log_level: str = "DEBUG",
    log_dir: Optional[Path] = None,
) -> None:
    """
    Setup development-optimized structured logging.

    Enables caller info, sets debug level, and outputs to console.

    Args:
        log_level: Log level for development
        log_dir: Log directory

    Example:
        setup_development_logging(log_level="DEBUG")
    """
    configure_structured_logging(
        log_level=log_level,
        log_dir=log_dir,
        enable_console=True,
        enable_file=True,
        enable_caller_info=True,  # Enable for debugging
        cache_logger_on_first_use=False,  # Disable caching for development
    )
