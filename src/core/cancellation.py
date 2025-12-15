"""
Cancellation token for safe job termination.

Propagates stop/pause signals throughout execution stack.
"""

import logging
from threading import Event
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CancellationReason(str, Enum):
    """Reason for cancellation."""
    USER_REQUEST = "user_request"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class CancellationToken:
    """
    Thread-safe cancellation token.

    Allows cooperative cancellation of long-running operations.
    """

    def __init__(self):
        """Initialize cancellation token."""
        self._cancelled = Event()
        self._paused = Event()
        self._reason: Optional[CancellationReason] = None
        self._message: Optional[str] = None

    def cancel(self, reason: CancellationReason = CancellationReason.USER_REQUEST, message: Optional[str] = None):
        """
        Request cancellation.

        Args:
            reason: Cancellation reason
            message: Optional message
        """
        self._reason = reason
        self._message = message
        self._cancelled.set()
        logger.info(f"Cancellation requested: {reason} - {message}")

    def pause(self):
        """Request pause."""
        self._paused.set()
        logger.info("Pause requested")

    def resume(self):
        """Resume from pause."""
        self._paused.clear()
        logger.info("Resume requested")

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancelled.is_set()

    def is_paused(self) -> bool:
        """Check if pause was requested."""
        return self._paused.is_set()

    def check(self):
        """
        Check cancellation status and raise if cancelled.

        Raises:
            CancellationError: If cancellation was requested
        """
        if self.is_cancelled():
            raise CancellationError(self._reason, self._message)

    def wait_while_paused(self, check_interval: float = 0.1):
        """
        Block while paused, checking for cancellation.

        Args:
            check_interval: How often to check for cancellation (seconds)

        Raises:
            CancellationError: If cancelled while paused
        """
        while self.is_paused():
            if self.is_cancelled():
                raise CancellationError(self._reason, self._message)

            # Sleep briefly
            import time
            time.sleep(check_interval)

    def get_reason(self) -> Optional[CancellationReason]:
        """Get cancellation reason."""
        return self._reason

    def get_message(self) -> Optional[str]:
        """Get cancellation message."""
        return self._message

    def reset(self):
        """Reset cancellation token."""
        self._cancelled.clear()
        self._paused.clear()
        self._reason = None
        self._message = None


class CancellationError(Exception):
    """Exception raised when operation is cancelled."""

    def __init__(self, reason: Optional[CancellationReason] = None, message: Optional[str] = None):
        """
        Initialize cancellation error.

        Args:
            reason: Cancellation reason
            message: Optional message
        """
        self.reason = reason or CancellationReason.USER_REQUEST
        self.message = message or f"Operation cancelled: {self.reason.value}"
        super().__init__(self.message)


class CancellableOperation:
    """
    Base class for cancellable operations.

    Provides common cancellation checking logic.
    """

    def __init__(self, token: Optional[CancellationToken] = None):
        """
        Initialize cancellable operation.

        Args:
            token: Cancellation token (creates new if None)
        """
        self.token = token or CancellationToken()

    def check_cancellation(self):
        """Check and handle cancellation/pause."""
        self.token.wait_while_paused()
        self.token.check()

    def is_cancelled(self) -> bool:
        """Check if operation is cancelled."""
        return self.token.is_cancelled()

    def is_paused(self) -> bool:
        """Check if operation is paused."""
        return self.token.is_paused()
