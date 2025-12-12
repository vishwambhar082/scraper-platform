"""
Task Router Module

Routes tasks to appropriate execution engines based on
task type, resource requirements, and availability.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionEngine(str, Enum):
    """Available execution engines."""
    LOCAL = "local"
    AIRFLOW = "airflow"
    CELERY = "celery"
    KUBERNETES = "kubernetes"


@dataclass
class RoutingRule:
    """Task routing rule."""

    pattern: str
    engine: ExecutionEngine
    priority: int = 0
    conditions: Dict[str, Any] = None

    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}


class TaskRouter:
    """
    Routes tasks to appropriate execution engines.

    Features:
    - Pattern-based routing
    - Load-based routing
    - Fallback support
    """

    def __init__(self):
        """Initialize task router."""
        self.rules: List[RoutingRule] = []
        self.default_engine = ExecutionEngine.LOCAL
        logger.info("Initialized TaskRouter")

    def add_rule(self, rule: RoutingRule) -> None:
        """Add routing rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.debug(f"Added routing rule: {rule.pattern} -> {rule.engine.value}")

    def route(self, task_name: str, task_config: Optional[Dict[str, Any]] = None) -> ExecutionEngine:
        """
        Route a task to an execution engine.

        Args:
            task_name: Task name
            task_config: Task configuration

        Returns:
            Selected execution engine
        """
        task_config = task_config or {}

        # Check rules
        for rule in self.rules:
            if self._matches_pattern(task_name, rule.pattern):
                if self._check_conditions(task_config, rule.conditions):
                    logger.info(f"Routing {task_name} to {rule.engine.value}")
                    return rule.engine

        # Use default
        logger.info(f"Routing {task_name} to default engine: {self.default_engine.value}")
        return self.default_engine

    def _matches_pattern(self, task_name: str, pattern: str) -> bool:
        """Check if task name matches pattern."""
        import re
        return bool(re.match(pattern, task_name))

    def _check_conditions(self, config: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """Check if configuration meets conditions."""
        for key, value in conditions.items():
            if config.get(key) != value:
                return False
        return True
