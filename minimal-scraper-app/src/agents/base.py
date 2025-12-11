"""Core agent primitives for the agentic orchestrator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Mapping, MutableMapping, Optional

from src.common.logging_utils import get_logger

log = get_logger("agents.base")


@dataclass(slots=True)
class AgentConfig:
    """Lightweight configuration passed to agents.

    Args:
        timeout: Maximum time (seconds) an agent should take to run.
        retries: Number of retry attempts for transient failures.
        backoff_seconds: Delay between retries.
        name: Optional explicit agent name override.
    """

    timeout: float = 30.0
    retries: int = 0
    backoff_seconds: float = 1.0
    name: Optional[str] = None


class AgentContext(MutableMapping[str, Any]):
    """Dict-like container that supports nested access via dotted paths."""

    def __init__(
        self,
        initial: Optional[Mapping[str, Any]] = None,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._data: dict[str, Any] = dict(initial or {})
        self.metadata: dict[str, Any] = dict(metadata or {})

    # MutableMapping API
    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._data)

    # Convenience helpers
    def get_nested(self, path: str, default: Any = None) -> Any:
        current: Any = self._data
        for part in path.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return default
        return current

    def set_nested(self, path: str, value: Any) -> None:
        parts = path.split(".")
        current = self._data
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], Mapping):
                current[part] = {}
            current = current[part]  # type: ignore[assignment]
        current[parts[-1]] = value

    def merge(self, other: Mapping[str, Any], *, overwrite: bool = True) -> None:
        """Merge another mapping into this context."""

        for key, value in other.items():
            if overwrite or key not in self._data:
                self._data[key] = value

    def copy(self) -> "AgentContext":
        return AgentContext(dict(self._data), metadata=dict(self.metadata))


class BaseAgent:
    """Base interface all agents must implement."""

    name: str

    def __init__(self, name: Optional[str] = None, config: Optional[AgentConfig] = None) -> None:
        self.name = name or self.__class__.__name__
        self.config = config or AgentConfig()

    def run(self, context: AgentContext) -> AgentContext:  # pragma: no cover - abstract
        raise NotImplementedError


__all__ = ["AgentConfig", "AgentContext", "BaseAgent"]
