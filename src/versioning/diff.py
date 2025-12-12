"""
Diff Module

Provides diff calculation for configuration and data changes.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Types of changes."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class Change:
    """Represents a single change."""

    path: str
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None


class DiffCalculator:
    """Calculates diffs between configurations."""

    def diff(self, old: Dict[str, Any], new: Dict[str, Any]) -> List[Change]:
        """
        Calculate diff between two dictionaries.

        Args:
            old: Old dictionary
            new: New dictionary

        Returns:
            List of changes
        """
        changes = []
        self._diff_recursive(old, new, "", changes)
        return changes

    def _diff_recursive(
        self,
        old: Any,
        new: Any,
        path: str,
        changes: List[Change]
    ) -> None:
        """Recursively diff nested structures."""
        if isinstance(old, dict) and isinstance(new, dict):
            # Compare dictionaries
            all_keys = set(old.keys()) | set(new.keys())

            for key in all_keys:
                new_path = f"{path}.{key}" if path else key

                if key not in old:
                    changes.append(Change(
                        path=new_path,
                        change_type=ChangeType.ADDED,
                        new_value=new[key]
                    ))
                elif key not in new:
                    changes.append(Change(
                        path=new_path,
                        change_type=ChangeType.REMOVED,
                        old_value=old[key]
                    ))
                else:
                    self._diff_recursive(old[key], new[key], new_path, changes)

        elif old != new:
            changes.append(Change(
                path=path,
                change_type=ChangeType.MODIFIED,
                old_value=old,
                new_value=new
            ))
