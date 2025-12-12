"""
Session Models Module

Defines data models for session management.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Session status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


@dataclass
class Session:
    """User session."""

    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    status: SessionStatus = SessionStatus.ACTIVE
    data: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == SessionStatus.ACTIVE

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "status": self.status.value,
            "data": self.data
        }


class SessionManager:
    """Manages user sessions."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, Session] = {}
        logger.info("Initialized SessionManager")

    def create_session(self, user_id: str) -> Session:
        """Create a new session."""
        import uuid
        session_id = str(uuid.uuid4())
        now = datetime.now()

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity=now
        )

        self.sessions[session_id] = session
        logger.info(f"Created session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
