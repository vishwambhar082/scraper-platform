"""Aggregates resource managers to avoid module-level globals."""

from __future__ import annotations

from typing import Mapping, Optional

from src.common.config_loader import load_config

from src.resource_manager.account_router import AccountRouter
from src.resource_manager.budget_tracker import BudgetTracker
from src.resource_manager.cost_tracker import CostTracker
from src.resource_manager.proxy_pool import ProxyPool


class ResourceManager:
    """Container for per-run resource dependencies."""

    def __init__(self, settings: Optional[Mapping[str, object]] = None):
        self.settings = settings or {}
        self.proxy_pool = ProxyPool(settings=self.settings)
        self.account_router = AccountRouter(settings=self.settings)
        self.cost_tracker = CostTracker()
        self.budget_tracker = BudgetTracker()


_default_manager: Optional[ResourceManager] = None


def get_default_resource_manager() -> ResourceManager:
    global _default_manager
    if _default_manager is None:
        # Lazy-load settings so the default manager picks up current config
        try:
            settings = load_config()
        except Exception:
            # Fall back to empty settings to avoid hard failure; account_router will
            # then rely on environment variables.
            settings = {}
        _default_manager = ResourceManager(settings=settings)
    return _default_manager


__all__ = ["ResourceManager", "get_default_resource_manager"]
