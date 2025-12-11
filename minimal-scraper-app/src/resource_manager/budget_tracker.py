# src/resource_manager/budget_tracker.py

from dataclasses import dataclass
from typing import Dict

from src.common.logging_utils import get_logger

log = get_logger("budget-tracker")


@dataclass
class BudgetState:
    limit: float
    spent: float = 0.0

    @property
    def remaining(self) -> float:
        return max(self.limit - self.spent, 0.0)


class BudgetTracker:
    """Instance-scoped budget tracker to avoid shared global state."""

    def __init__(self) -> None:
        self._budgets: Dict[str, BudgetState] = {}

    def set_daily_budget(self, source: str, limit: float) -> None:
        self._budgets[source] = BudgetState(limit=limit)
        log.info("Budget set for %s: %.4f", source, limit)

    def can_spend(self, source: str, amount: float) -> bool:
        bs = self._budgets.get(source)
        if bs is None:
            return True
        return bs.remaining >= amount

    def record_spend(self, source: str, amount: float) -> None:
        bs = self._budgets.setdefault(source, BudgetState(limit=float("inf")))
        bs.spent += amount
        log.debug(
            "Spend recorded for %s: +%.4f (remaining=%.4f)",
            source,
            amount,
            bs.remaining,
        )


_DEFAULT_BUDGET_TRACKER = BudgetTracker()


def set_daily_budget(source: str, limit: float) -> None:
    _DEFAULT_BUDGET_TRACKER.set_daily_budget(source, limit)


def can_spend(source: str, amount: float) -> bool:
    return _DEFAULT_BUDGET_TRACKER.can_spend(source, amount)


def record_spend(source: str, amount: float) -> None:
    _DEFAULT_BUDGET_TRACKER.record_spend(source, amount)
