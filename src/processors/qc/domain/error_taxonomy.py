"""
Error Taxonomy Module

Defines taxonomy of QC errors for structured error classification.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categories."""
    DATA_QUALITY = "data_quality"
    SCHEMA_VIOLATION = "schema_violation"
    BUSINESS_RULE = "business_rule"
    TECHNICAL = "technical"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ErrorDefinition:
    """Definition of an error type."""

    code: str
    name: str
    category: ErrorCategory
    severity: ErrorSeverity
    description: str


class ErrorTaxonomy:
    """Manages error taxonomy."""

    def __init__(self):
        """Initialize error taxonomy."""
        self.definitions = self._load_definitions()
        logger.info("Initialized ErrorTaxonomy")

    def _load_definitions(self) -> Dict[str, ErrorDefinition]:
        """Load error definitions."""
        return {
            "E001": ErrorDefinition(
                code="E001",
                name="Missing Required Field",
                category=ErrorCategory.DATA_QUALITY,
                severity=ErrorSeverity.CRITICAL,
                description="Required field is missing or null"
            ),
            "E002": ErrorDefinition(
                code="E002",
                name="Invalid Format",
                category=ErrorCategory.SCHEMA_VIOLATION,
                severity=ErrorSeverity.HIGH,
                description="Field has invalid format"
            )
        }

    def get_definition(self, error_code: str) -> Optional[ErrorDefinition]:
        """Get error definition by code."""
        return self.definitions.get(error_code)
