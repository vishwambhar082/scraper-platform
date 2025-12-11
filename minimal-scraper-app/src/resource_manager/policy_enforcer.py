# file: src/resource_manager/policy_enforcer.py
"""
Policy enforcement for resource usage (concurrency, budget, rate limits, etc.).
"""

from __future__ import annotations

from typing import Dict, Optional

from src.common.logging_utils import get_logger
from src.resource_manager.cost_tracker import get_cost

log = get_logger("policy-enforcer")


class PolicyViolation(Exception):
    """Raised when a policy check fails."""

    def __init__(self, message: str, policy_key: Optional[str] = None):
        super().__init__(message)
        self.policy_key = policy_key


class PolicyEnforcer:
    """Enforces resource usage policies for scraper runs."""

    def __init__(self):
        self._active_runs: Dict[str, int] = {}  # source -> count
        self._budget_limits: Dict[str, float] = {}  # source -> max budget

    def check_concurrency(self, source: str, max_concurrent: Optional[int]) -> bool:
        """Check if a new run can start given concurrency limits."""
        if max_concurrent is None:
            return True

        current = self._active_runs.get(source, 0)
        if current >= max_concurrent:
            log.warning(
                "Concurrency limit exceeded",
                extra={"source": source, "current": current, "max": max_concurrent},
            )
            return False
        return True

    def check_budget(self, source: str, max_budget: Optional[float]) -> bool:
        """Check if a run can start given budget limits."""
        if max_budget is None:
            return True

        current_cost = get_cost(f"{source}:total")
        if current_cost >= max_budget:
            log.warning(
                "Budget limit exceeded",
                extra={"source": source, "current": current_cost, "max": max_budget},
            )
            return False
        return True

    def register_run_start(self, source: str) -> None:
        """Register that a run has started."""
        self._active_runs[source] = self._active_runs.get(source, 0) + 1

    def register_run_end(self, source: str) -> None:
        """Register that a run has ended."""
        current = self._active_runs.get(source, 0)
        if current > 0:
            self._active_runs[source] = current - 1
        else:
            log.warning("Attempted to end run when count was already zero", extra={"source": source})

    def can_run(self, source: str, policy: Dict[str, object]) -> bool:
        """
        Evaluate if a run can proceed given the policy.

        Args:
            source: Source name
            policy: Policy dict with keys like:
                - max_concurrency: int (optional)
                - max_budget: float (optional)
                - max_cost_per_run: float (optional)

        Returns:
            True if the run can proceed, False otherwise
        """
        max_concurrent = policy.get("max_concurrency")
        max_budget = policy.get("max_budget")

        if not self.check_concurrency(source, max_concurrent):
            return False

        if not self.check_budget(source, max_budget):
            return False

        return True

    def enforce(self, source: str, policy: Dict[str, object]) -> None:
        """
        Enforce policy and raise PolicyViolation if check fails.

        Raises:
            PolicyViolation: If policy check fails
        """
        if not self.can_run(source, policy):
            raise PolicyViolation(
                f"Policy check failed for source '{source}'",
                policy_key=source,
            )


_DEFAULT_ENFORCER = PolicyEnforcer()


def can_run(policy: Dict[str, object], source: str = "default") -> bool:
    """
    Check if a run can proceed given the policy.

    Args:
        policy: Policy dict with concurrency/budget limits
        source: Source name (default: "default")

    Returns:
        True if the run can proceed, False otherwise
    """
    return _DEFAULT_ENFORCER.can_run(source, policy)


def enforce(policy: Dict[str, object], source: str = "default") -> None:
    """
    Enforce policy and raise PolicyViolation if check fails.

    Args:
        policy: Policy dict with concurrency/budget limits
        source: Source name (default: "default")

    Raises:
        PolicyViolation: If policy check fails
    """
    _DEFAULT_ENFORCER.enforce(source, policy)
