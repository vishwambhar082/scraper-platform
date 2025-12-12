"""
Audit Logger Module

High-level audit logging API with convenience methods for common audit events.
Provides decorators and context managers for automatic audit trail creation.

This module wraps the lower-level audit_log.py with user-friendly APIs.

Author: Scraper Platform Team
"""

import logging
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


# Import from existing audit_log module
try:
    from .audit_log import log_event, AuditEvent
    from .models import AuditAction
except ImportError:
    logger.warning("Could not import audit_log, using fallback implementation")
    # Fallback for standalone usage
    from dataclasses import dataclass
    from enum import Enum

    class AuditAction(str, Enum):
        """Audit action types."""
        CREATE = "create"
        UPDATE = "update"
        DELETE = "delete"
        ACCESS = "access"
        EXECUTE = "execute"

    @dataclass
    class AuditEvent:
        ts: str
        actor: str
        action: str
        entity_type: str
        entity_id: str
        metadata: Dict[str, Any]
        prev_hash: Optional[str]
        hash: Optional[str] = None

    def log_event(
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Fallback log_event implementation."""
        event = AuditEvent(
            ts=datetime.utcnow().isoformat(),
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
            prev_hash=None,
            hash=None
        )
        logger.info(f"AUDIT: {actor} {action} {entity_type}:{entity_id}")
        return event


class AuditLogger:
    """
    High-level audit logger with convenience methods.

    Features:
    - Automatic actor tracking
    - Structured logging
    - Decorator support
    - Context manager support
    """

    def __init__(self, default_actor: str = "system"):
        """
        Initialize audit logger.

        Args:
            default_actor: Default actor name for events
        """
        self.default_actor = default_actor
        logger.info(f"Initialized AuditLogger with actor: {default_actor}")

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        actor: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            action: Action type (create, update, delete, etc.)
            entity_type: Type of entity being acted upon
            entity_id: Entity identifier
            actor: Actor performing the action (defaults to default_actor)
            metadata: Additional event metadata

        Returns:
            AuditEvent instance
        """
        actor = actor or self.default_actor
        return log_event(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata
        )

    def log_create(
        self,
        entity_type: str,
        entity_id: str,
        actor: Optional[str] = None,
        **metadata
    ) -> AuditEvent:
        """Log a CREATE event."""
        return self.log(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=metadata
        )

    def log_update(
        self,
        entity_type: str,
        entity_id: str,
        actor: Optional[str] = None,
        **metadata
    ) -> AuditEvent:
        """Log an UPDATE event."""
        return self.log(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=metadata
        )

    def log_delete(
        self,
        entity_type: str,
        entity_id: str,
        actor: Optional[str] = None,
        **metadata
    ) -> AuditEvent:
        """Log a DELETE event."""
        return self.log(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=metadata
        )

    def log_access(
        self,
        entity_type: str,
        entity_id: str,
        actor: Optional[str] = None,
        **metadata
    ) -> AuditEvent:
        """Log an ACCESS event."""
        return self.log(
            action=AuditAction.ACCESS,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=metadata
        )

    def log_execute(
        self,
        entity_type: str,
        entity_id: str,
        actor: Optional[str] = None,
        **metadata
    ) -> AuditEvent:
        """Log an EXECUTE event."""
        return self.log(
            action=AuditAction.EXECUTE,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=metadata
        )

    @contextmanager
    def audit_context(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        actor: Optional[str] = None
    ):
        """
        Context manager for auditing operations.

        Logs start and completion (or failure) of an operation.

        Example:
            with audit_logger.audit_context("process", "pipeline", "alfabeta"):
                # Do work
                pass
        """
        actor = actor or self.default_actor
        start_metadata = {"status": "started"}

        # Log start
        self.log(action, entity_type, entity_id, actor, start_metadata)

        try:
            yield
            # Log success
            end_metadata = {"status": "completed"}
            self.log(action, entity_type, entity_id, actor, end_metadata)

        except Exception as e:
            # Log failure
            error_metadata = {"status": "failed", "error": str(e)}
            self.log(action, entity_type, entity_id, actor, error_metadata)
            raise


def audit_function(
    entity_type: str,
    entity_id_param: str = "entity_id",
    action: str = "execute"
):
    """
    Decorator to automatically audit function calls.

    Args:
        entity_type: Type of entity
        entity_id_param: Parameter name containing entity ID
        action: Action type

    Example:
        @audit_function("pipeline", entity_id_param="source")
        def run_pipeline(source: str):
            # Function will be audited
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract entity_id from kwargs
            entity_id = kwargs.get(entity_id_param, "unknown")

            # Create audit logger
            audit_logger = AuditLogger(default_actor="system")

            # Log start
            audit_logger.log(
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                metadata={"status": "started", "function": func.__name__}
            )

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Log success
                audit_logger.log(
                    action=action,
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    metadata={"status": "completed", "function": func.__name__}
                )

                return result

            except Exception as e:
                # Log failure
                audit_logger.log(
                    action=action,
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    metadata={
                        "status": "failed",
                        "function": func.__name__,
                        "error": str(e)
                    }
                )
                raise

        return wrapper
    return decorator


# Global audit logger instance
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(actor: str = "system") -> AuditLogger:
    """
    Get or create the global audit logger instance.

    Args:
        actor: Default actor for the logger

    Returns:
        AuditLogger instance
    """
    global _global_audit_logger

    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger(default_actor=actor)

    return _global_audit_logger


# Convenience functions for direct usage

def audit_create(
    entity_type: str,
    entity_id: str,
    actor: str = "system",
    **metadata
) -> AuditEvent:
    """Convenience function to log a CREATE event."""
    logger_instance = get_audit_logger(actor)
    return logger_instance.log_create(entity_type, entity_id, actor, **metadata)


def audit_update(
    entity_type: str,
    entity_id: str,
    actor: str = "system",
    **metadata
) -> AuditEvent:
    """Convenience function to log an UPDATE event."""
    logger_instance = get_audit_logger(actor)
    return logger_instance.log_update(entity_type, entity_id, actor, **metadata)


def audit_delete(
    entity_type: str,
    entity_id: str,
    actor: str = "system",
    **metadata
) -> AuditEvent:
    """Convenience function to log a DELETE event."""
    logger_instance = get_audit_logger(actor)
    return logger_instance.log_delete(entity_type, entity_id, actor, **metadata)


def audit_access(
    entity_type: str,
    entity_id: str,
    actor: str = "system",
    **metadata
) -> AuditEvent:
    """Convenience function to log an ACCESS event."""
    logger_instance = get_audit_logger(actor)
    return logger_instance.log_access(entity_type, entity_id, actor, **metadata)


def audit_execute(
    entity_type: str,
    entity_id: str,
    actor: str = "system",
    **metadata
) -> AuditEvent:
    """Convenience function to log an EXECUTE event."""
    logger_instance = get_audit_logger(actor)
    return logger_instance.log_execute(entity_type, entity_id, actor, **metadata)


__all__ = [
    "AuditLogger",
    "audit_function",
    "get_audit_logger",
    "audit_create",
    "audit_update",
    "audit_delete",
    "audit_access",
    "audit_execute",
    "AuditEvent",
    "AuditAction",
]
