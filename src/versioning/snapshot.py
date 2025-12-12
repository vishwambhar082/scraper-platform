"""
Snapshot Module

Provides snapshot functionality for data and configuration versioning.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages data and configuration snapshots."""

    def __init__(self, storage_path: Path = Path("snapshots")):
        """
        Initialize snapshot manager.

        Args:
            storage_path: Path to store snapshots
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized SnapshotManager at {storage_path}")

    def create_snapshot(
        self,
        data: Dict[str, Any],
        name: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Create a snapshot.

        Args:
            data: Data to snapshot
            name: Snapshot name
            metadata: Optional metadata

        Returns:
            Snapshot ID
        """
        timestamp = datetime.now()
        snapshot_id = f"{name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        snapshot = {
            "id": snapshot_id,
            "name": name,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata or {},
            "data": data
        }

        # Save to file
        file_path = self.storage_path / f"{snapshot_id}.json"
        with open(file_path, 'w') as f:
            json.dump(snapshot, f, indent=2)

        logger.info(f"Created snapshot: {snapshot_id}")
        return snapshot_id

    def load_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Load a snapshot.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            Snapshot data
        """
        file_path = self.storage_path / f"{snapshot_id}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_id}")

        with open(file_path, 'r') as f:
            snapshot = json.load(f)

        logger.info(f"Loaded snapshot: {snapshot_id}")
        return snapshot["data"]
