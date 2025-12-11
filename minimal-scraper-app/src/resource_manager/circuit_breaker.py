# src/resource_manager/circuit_breaker.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

from src.common.errors import CircuitOpenError
from src.common.logging_utils import get_logger

log = get_logger("circuit-breaker")


@dataclass
class CircuitState:
    failure_threshold: int
    reset_timeout: timedelta
    failures: int = 0
    opened_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        return datetime.utcnow() < self.opened_at + self.reset_timeout

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold and self.opened_at is None:
            self.opened_at = datetime.utcnow()
            log.warning("Circuit opened (failures=%d)", self.failures)

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None


_CIRCUITS: Dict[str, CircuitState] = {}  # key (e.g. source) -> circuit


def get_circuit(key: str, failure_threshold: int = 5, reset_seconds: int = 300) -> CircuitState:
    cs = _CIRCUITS.get(key)
    if cs is None:
        cs = CircuitState(
            failure_threshold=failure_threshold,
            reset_timeout=timedelta(seconds=reset_seconds),
        )
        _CIRCUITS[key] = cs
    return cs


def guard_call(key: str, failure_threshold: int = 5, reset_seconds: int = 300) -> None:
    cs = get_circuit(key, failure_threshold, reset_seconds)
    if cs.is_open:
        raise CircuitOpenError(f"Circuit for {key} is open")


def record_success(key: str) -> None:
    get_circuit(key).record_success()


def record_failure(key: str) -> None:
    get_circuit(key).record_failure()
