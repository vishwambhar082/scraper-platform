"""
UI logging handler that captures log messages and forwards them to the UI.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal


class UILoggingHandler(logging.Handler, QObject):
    """Logging handler that emits signals for UI updates."""
    
    message_logged = Signal(str, str)  # level, message
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        logging.Handler.__init__(self)
        QObject.__init__(self, parent)
        # Use simple formatter to avoid thread issues
        self.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        # Store parent reference to avoid threading issues
        self._parent = parent
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record as a signal."""
        try:
            # Format the record safely
            msg = self.format(record)
            level = record.levelname
            # Emit signal safely (Qt handles thread safety)
            if self._parent is not None:
                self.message_logged.emit(level, msg)
        except Exception:
            # Silently handle errors to avoid recursion
            pass

