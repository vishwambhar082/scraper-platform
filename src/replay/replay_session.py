"""
Replay session data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ReplaySession:
    """Complete replay session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    screenshots: List[Dict[str, Any]] = field(default_factory=list)
    network_log: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.utcnow() - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'actions': self.actions,
            'screenshots': self.screenshots,
            'network_log': self.network_log,
            'metadata': self.metadata,
            'duration_seconds': self.duration_seconds()
        }
