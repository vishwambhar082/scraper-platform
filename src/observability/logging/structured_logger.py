"""
Structured Logger Module

Provides structured logging with JSON formatting and enrichment.

Author: Scraper Platform Team
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StructuredLogger:
    """
    Structured logger with JSON output.

    Features:
    - JSON formatting
    - Field enrichment
    - Context propagation
    """

    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            context: Default context to include in logs
        """
        self.name = name
        self.context = context or {}
        self.base_logger = logging.getLogger(name)

    def _build_log_entry(
        self,
        level: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Build structured log entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "logger": self.name,
            "level": level,
            "message": message
        }

        # Add context
        entry.update(self.context)

        # Add additional fields
        entry.update(kwargs)

        return entry

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        entry = self._build_log_entry("INFO", message, **kwargs)
        self.base_logger.info(json.dumps(entry))

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        entry = self._build_log_entry("ERROR", message, **kwargs)
        self.base_logger.error(json.dumps(entry))

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        entry = self._build_log_entry("WARNING", message, **kwargs)
        self.base_logger.warning(json.dumps(entry))

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        entry = self._build_log_entry("DEBUG", message, **kwargs)
        self.base_logger.debug(json.dumps(entry))
