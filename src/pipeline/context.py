"""
Pipeline Context Module

Manages execution context for pipeline runs.
Provides shared state, variable management, and context isolation.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)


@dataclass
class ContextMetadata:
    """Metadata for execution context."""

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    execution_id: Optional[str] = None
    pipeline_name: Optional[str] = None
    user: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "execution_id": self.execution_id,
            "pipeline_name": self.pipeline_name,
            "user": self.user,
            "tags": self.tags
        }


class ExecutionContext:
    """
    Execution context for pipeline runs.

    Features:
    - Variable storage and retrieval
    - Context isolation
    - Thread-safe operations
    - History tracking
    - Middleware support
    """

    def __init__(
        self,
        initial_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[ContextMetadata] = None
    ):
        """
        Initialize execution context.

        Args:
            initial_data: Initial context data
            metadata: Context metadata
        """
        self._data: Dict[str, Any] = initial_data or {}
        self._metadata = metadata or ContextMetadata()
        self._lock = threading.RLock()
        self._history: List[Dict[str, Any]] = []
        self._middleware: List[Callable] = []
        logger.debug("Initialized ExecutionContext")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from context.

        Args:
            key: Context key
            default: Default value if not found

        Returns:
            Context value
        """
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set value in context.

        Args:
            key: Context key
            value: Value to set
        """
        with self._lock:
            old_value = self._data.get(key)

            # Apply middleware
            for middleware in self._middleware:
                value = middleware(key, value, old_value)

            self._data[key] = value
            self._metadata.updated_at = datetime.now()

            # Track in history
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "set",
                "key": key,
                "value": str(value)[:100]  # Truncate for logging
            })

            logger.debug(f"Context set: {key} = {value}")

    def update(self, data: Dict[str, Any]) -> None:
        """
        Update multiple values.

        Args:
            data: Dictionary of values to update
        """
        with self._lock:
            for key, value in data.items():
                self.set(key, value)

    def delete(self, key: str) -> bool:
        """
        Delete value from context.

        Args:
            key: Context key

        Returns:
            True if deleted
        """
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._metadata.updated_at = datetime.now()

                self._history.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "delete",
                    "key": key
                })

                logger.debug(f"Context deleted: {key}")
                return True
            return False

    def has(self, key: str) -> bool:
        """
        Check if key exists in context.

        Args:
            key: Context key

        Returns:
            True if exists
        """
        with self._lock:
            return key in self._data

    def get_all(self) -> Dict[str, Any]:
        """
        Get all context data.

        Returns:
            Copy of context data
        """
        with self._lock:
            return self._data.copy()

    def clear(self) -> None:
        """Clear all context data."""
        with self._lock:
            self._data.clear()
            self._metadata.updated_at = datetime.now()
            logger.debug("Context cleared")

    def get_metadata(self) -> ContextMetadata:
        """Get context metadata."""
        return self._metadata

    def get_history(self) -> List[Dict[str, Any]]:
        """Get context modification history."""
        with self._lock:
            return self._history.copy()

    def add_middleware(self, middleware: Callable) -> None:
        """
        Add middleware function.

        Args:
            middleware: Middleware function (key, new_value, old_value) -> value
        """
        self._middleware.append(middleware)
        logger.debug("Added context middleware")

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        with self._lock:
            return {
                "data": self._data.copy(),
                "metadata": self._metadata.to_dict(),
                "history_size": len(self._history)
            }

    @contextmanager
    def scoped(self, **kwargs):
        """
        Create a scoped context.

        Temporarily adds variables, then removes them on exit.

        Args:
            **kwargs: Variables to add
        """
        # Save original values
        original_values = {}
        for key in kwargs:
            if self.has(key):
                original_values[key] = self.get(key)

        try:
            # Set scoped values
            self.update(kwargs)
            yield self

        finally:
            # Restore original values
            for key in kwargs:
                if key in original_values:
                    self.set(key, original_values[key])
                else:
                    self.delete(key)


class ContextManager:
    """
    Manager for multiple execution contexts.

    Provides context pooling and lifecycle management.
    """

    def __init__(self):
        """Initialize context manager."""
        self.contexts: Dict[str, ExecutionContext] = {}
        self._lock = threading.RLock()
        logger.info("Initialized ContextManager")

    def create_context(
        self,
        context_id: str,
        initial_data: Optional[Dict[str, Any]] = None,
        **metadata_kwargs
    ) -> ExecutionContext:
        """
        Create a new execution context.

        Args:
            context_id: Context identifier
            initial_data: Initial context data
            **metadata_kwargs: Metadata fields

        Returns:
            Created context
        """
        with self._lock:
            metadata = ContextMetadata(**metadata_kwargs)
            context = ExecutionContext(initial_data, metadata)
            self.contexts[context_id] = context
            logger.info(f"Created context: {context_id}")
            return context

    def get_context(self, context_id: str) -> Optional[ExecutionContext]:
        """
        Get context by ID.

        Args:
            context_id: Context identifier

        Returns:
            Context or None if not found
        """
        with self._lock:
            return self.contexts.get(context_id)

    def delete_context(self, context_id: str) -> bool:
        """
        Delete a context.

        Args:
            context_id: Context identifier

        Returns:
            True if deleted
        """
        with self._lock:
            if context_id in self.contexts:
                del self.contexts[context_id]
                logger.info(f"Deleted context: {context_id}")
                return True
            return False

    def list_contexts(self) -> List[str]:
        """
        List all context IDs.

        Returns:
            List of context IDs
        """
        with self._lock:
            return list(self.contexts.keys())

    def cleanup_old_contexts(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old contexts.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            Number of contexts cleaned up
        """
        with self._lock:
            now = datetime.now()
            to_delete = []

            for context_id, context in self.contexts.items():
                age = (now - context.get_metadata().created_at).total_seconds()
                if age > max_age_seconds:
                    to_delete.append(context_id)

            for context_id in to_delete:
                self.delete_context(context_id)

            logger.info(f"Cleaned up {len(to_delete)} old contexts")
            return len(to_delete)


# Global context manager
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """
    Get global context manager.

    Returns:
        Context manager singleton
    """
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
