"""
Quality Control Rules Domain Model.

This module defines the core domain entities for QC rules without any
implementation details or external dependencies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Protocol

Record = Dict[str, Any]


class SeverityLevel(str, Enum):
    """Severity levels for QC rules."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class QCRuleResult:
    """Result of applying a single QC rule to a record."""
    rule_id: str
    passed: bool
    severity: SeverityLevel
    message: str


@dataclass(frozen=True)
class QCConfiguration:
    """Configuration for QC rule execution."""
    fail_on_warning: bool = False
    stop_on_first_error: bool = False


class QCRecordValidator(Protocol):
    """Protocol for validating a single record against a rule."""
    
    def validate(self, record: Record) -> QCRuleResult:
        """Validate a record and return the result."""
        ...


class QCResultEvaluator(Protocol):
    """Protocol for evaluating overall QC results."""
    
    def should_pass(self, results: list[QCRuleResult]) -> bool:
        """Determine if the overall QC check should pass based on results."""
        ...