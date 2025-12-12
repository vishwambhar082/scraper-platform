"""
Audit Models Module

Defines data models for audit logging.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Audit action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    VIEW = "view"


@dataclass
class AuditEntry:
    """Audit log entry."""

    timestamp: datetime
    action: AuditAction
    resource_type: str
    resource_id: str
    user: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "user": self.user,
            "details": self.details or {}
        }


class AuditLogger:
    """Audit logger."""

    def __init__(self):
        """Initialize audit logger."""
        self.entries: List[AuditEntry] = []
        logger.info("Initialized AuditLogger")

    def log(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        user: Optional[str] = None,
        **details
    ) -> None:
        """
        Log an audit entry.

        Args:
            action: Action type
            resource_type: Resource type
            resource_id: Resource ID
            user: User performing action
            **details: Additional details
        """
        entry = AuditEntry(
            timestamp=datetime.now(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user=user,
            details=details
        )

        self.entries.append(entry)
        logger.debug(f"Audit: {action.value} {resource_type}/{resource_id}")
