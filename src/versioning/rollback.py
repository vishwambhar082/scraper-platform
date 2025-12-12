"""
Rollback Module

Provides rollback functionality for configuration changes.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages configuration rollbacks."""

    def __init__(self):
        """Initialize rollback manager."""
        self.history: list = []
        logger.info("Initialized RollbackManager")

    def save_snapshot(self, config: Dict[str, Any], label: str) -> str:
        """
        Save configuration snapshot.

        Args:
            config: Configuration to save
            label: Snapshot label

        Returns:
            Snapshot ID
        """
        snapshot_id = f"snapshot_{len(self.history)}"
        self.history.append({
            "id": snapshot_id,
            "label": label,
            "config": config.copy(),
            "timestamp": datetime.now()
        })
        logger.info(f"Saved snapshot: {snapshot_id}")
        return snapshot_id

    def rollback(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Rollback to a snapshot.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            Snapshot configuration or None
        """
        for snapshot in self.history:
            if snapshot["id"] == snapshot_id:
                logger.info(f"Rolling back to snapshot: {snapshot_id}")
                return snapshot["config"].copy()

        logger.warning(f"Snapshot not found: {snapshot_id}")
        return None
