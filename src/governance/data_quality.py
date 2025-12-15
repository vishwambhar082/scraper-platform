"""
Data Quality Module

Enforces data quality standards and performs quality checks on scraped data.
Provides metrics and reporting for data quality monitoring.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QualityDimension(str, Enum):
    """Data quality dimensions."""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"
    TIMELINESS = "timeliness"


class QualityCheckResult(str, Enum):
    """Quality check result."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class QualityIssue:
    """Data quality issue."""

    dimension: QualityDimension
    severity: str  # "critical", "major", "minor"
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dimension": self.dimension.value,
            "severity": self.severity,
            "message": self.message,
            "field": self.field,
            "value": str(self.value) if self.value is not None else None,
            "suggestion": self.suggestion
        }


@dataclass
class QualityMetrics:
    """Data quality metrics."""

    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    consistency_score: float = 0.0
    overall_score: float = 0.0
    issues: List[QualityIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "completeness_score": self.completeness_score,
            "accuracy_score": self.accuracy_score,
            "consistency_score": self.consistency_score,
            "overall_score": self.overall_score,
            "issue_count": len(self.issues)
        }


@dataclass
class QualityCheckReport:
    """Data quality check report."""

    timestamp: datetime
    dataset_name: str
    metrics: QualityMetrics
    passed: bool
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "dataset_name": self.dataset_name,
            "metrics": self.metrics.to_dict(),
            "passed": self.passed,
            "execution_time": self.execution_time
        }


class QualityRule:
    """Base class for quality rules."""

    def __init__(self, name: str, dimension: QualityDimension):
        """
        Initialize quality rule.

        Args:
            name: Rule name
            dimension: Quality dimension
        """
        self.name = name
        self.dimension = dimension

    def check(self, record: Dict[str, Any]) -> Optional[QualityIssue]:
        """
        Check if record passes this rule.

        Args:
            record: Record to check

        Returns:
            QualityIssue if check fails, None if passes
        """
        raise NotImplementedError


class CompletenessRule(QualityRule):
    """Rule for checking data completeness."""

    def __init__(self, required_fields: List[str]):
        """
        Initialize completeness rule.

        Args:
            required_fields: List of required field names
        """
        super().__init__("completeness", QualityDimension.COMPLETENESS)
        self.required_fields = required_fields

    def check(self, record: Dict[str, Any]) -> Optional[QualityIssue]:
        """Check for missing required fields."""
        missing_fields = []

        for field in self.required_fields:
            value = record.get(field)
            if value is None or value == "":
                missing_fields.append(field)

        if missing_fields:
            return QualityIssue(
                dimension=self.dimension,
                severity="major",
                message=f"Missing required fields: {', '.join(missing_fields)}",
                field=missing_fields[0],
                suggestion="Ensure all required fields are scraped"
            )

        return None


class FormatRule(QualityRule):
    """Rule for checking field formats."""

    def __init__(self, field: str, format_checker: Callable[[Any], bool]):
        """
        Initialize format rule.

        Args:
            field: Field name to check
            format_checker: Function that returns True if format is valid
        """
        super().__init__(f"format_{field}", QualityDimension.VALIDITY)
        self.field = field
        self.format_checker = format_checker

    def check(self, record: Dict[str, Any]) -> Optional[QualityIssue]:
        """Check field format."""
        value = record.get(self.field)

        if value is None:
            return None  # Handled by completeness rule

        if not self.format_checker(value):
            return QualityIssue(
                dimension=self.dimension,
                severity="minor",
                message=f"Field '{self.field}' has invalid format",
                field=self.field,
                value=value,
                suggestion="Check format specification and parsing logic"
            )

        return None


class RangeRule(QualityRule):
    """Rule for checking numeric ranges."""

    def __init__(
        self,
        field: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ):
        """
        Initialize range rule.

        Args:
            field: Field name to check
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        """
        super().__init__(f"range_{field}", QualityDimension.VALIDITY)
        self.field = field
        self.min_value = min_value
        self.max_value = max_value

    def check(self, record: Dict[str, Any]) -> Optional[QualityIssue]:
        """Check if value is in range."""
        value = record.get(self.field)

        if value is None:
            return None

        try:
            numeric_value = float(value)

            if self.min_value is not None and numeric_value < self.min_value:
                return QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    message=f"Field '{self.field}' below minimum: {numeric_value} < {self.min_value}",
                    field=self.field,
                    value=value
                )

            if self.max_value is not None and numeric_value > self.max_value:
                return QualityIssue(
                    dimension=self.dimension,
                    severity="major",
                    message=f"Field '{self.field}' above maximum: {numeric_value} > {self.max_value}",
                    field=self.field,
                    value=value
                )

        except (ValueError, TypeError):
            return QualityIssue(
                dimension=self.dimension,
                severity="major",
                message=f"Field '{self.field}' is not numeric",
                field=self.field,
                value=value
            )

        return None


class DataQualityChecker:
    """
    Main data quality checker.

    Features:
    - Configurable quality rules
    - Multi-dimensional quality assessment
    - Detailed quality reporting
    - Threshold-based pass/fail
    """

    def __init__(self, rules: Optional[List[QualityRule]] = None):
        """
        Initialize data quality checker.

        Args:
            rules: List of quality rules to apply
        """
        self.rules = rules or []
        logger.info(f"Initialized DataQualityChecker with {len(self.rules)} rules")

    def add_rule(self, rule: QualityRule) -> None:
        """
        Add a quality rule.

        Args:
            rule: Quality rule to add
        """
        self.rules.append(rule)
        logger.debug(f"Added rule: {rule.name}")

    def check_record(self, record: Dict[str, Any]) -> List[QualityIssue]:
        """
        Check a single record against all rules.

        Args:
            record: Record to check

        Returns:
            List of quality issues found
        """
        issues = []

        for rule in self.rules:
            try:
                issue = rule.check(record)
                if issue:
                    issues.append(issue)
            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {e}")
                issues.append(QualityIssue(
                    dimension=rule.dimension,
                    severity="critical",
                    message=f"Rule '{rule.name}' failed to execute: {str(e)}"
                ))

        return issues

    def check_dataset(
        self,
        records: List[Dict[str, Any]],
        dataset_name: str = "dataset",
        min_score: float = 0.7
    ) -> QualityCheckReport:
        """
        Check quality of entire dataset.

        Args:
            records: List of records to check
            dataset_name: Name of dataset
            min_score: Minimum quality score to pass (0.0 to 1.0)

        Returns:
            Quality check report
        """
        logger.info(f"Checking quality of {len(records)} records in '{dataset_name}'")
        start_time = datetime.now()

        metrics = QualityMetrics()
        metrics.total_records = len(records)

        all_issues: List[QualityIssue] = []
        valid_count = 0

        # Check each record
        for record in records:
            issues = self.check_record(record)
            all_issues.extend(issues)

            # Count as valid if no critical issues
            critical_issues = [i for i in issues if i.severity == "critical"]
            if not critical_issues:
                valid_count += 1

        metrics.valid_records = valid_count
        metrics.invalid_records = metrics.total_records - valid_count
        metrics.issues = all_issues

        # Calculate scores
        metrics.completeness_score = self._calculate_completeness_score(records, all_issues)
        metrics.accuracy_score = self._calculate_accuracy_score(records, all_issues)
        metrics.consistency_score = self._calculate_consistency_score(records, all_issues)

        # Overall score (weighted average)
        metrics.overall_score = (
            metrics.completeness_score * 0.4 +
            metrics.accuracy_score * 0.3 +
            metrics.consistency_score * 0.3
        )

        # Determine pass/fail
        passed = metrics.overall_score >= min_score

        # Calculate execution time
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        report = QualityCheckReport(
            timestamp=start_time,
            dataset_name=dataset_name,
            metrics=metrics,
            passed=passed,
            execution_time=execution_time
        )

        logger.info(
            f"Quality check complete: score={metrics.overall_score:.2f}, "
            f"passed={passed}, issues={len(all_issues)}"
        )

        return report

    def _calculate_completeness_score(
        self,
        records: List[Dict[str, Any]],
        issues: List[QualityIssue]
    ) -> float:
        """Calculate completeness score."""
        if not records:
            return 0.0

        completeness_issues = [
            i for i in issues
            if i.dimension == QualityDimension.COMPLETENESS
        ]

        # Each completeness issue reduces score
        penalty = len(completeness_issues) * 0.01
        return max(1.0 - penalty, 0.0)

    def _calculate_accuracy_score(
        self,
        records: List[Dict[str, Any]],
        issues: List[QualityIssue]
    ) -> float:
        """Calculate accuracy score."""
        if not records:
            return 0.0

        accuracy_issues = [
            i for i in issues
            if i.dimension in {QualityDimension.ACCURACY, QualityDimension.VALIDITY}
        ]

        # Weight by severity
        penalty = 0.0
        for issue in accuracy_issues:
            if issue.severity == "critical":
                penalty += 0.05
            elif issue.severity == "major":
                penalty += 0.02
            else:
                penalty += 0.01

        return max(1.0 - penalty, 0.0)

    def _calculate_consistency_score(
        self,
        records: List[Dict[str, Any]],
        issues: List[QualityIssue]
    ) -> float:
        """Calculate consistency score."""
        if not records:
            return 0.0

        consistency_issues = [
            i for i in issues
            if i.dimension == QualityDimension.CONSISTENCY
        ]

        penalty = len(consistency_issues) * 0.02
        return max(1.0 - penalty, 0.0)


def create_standard_checker() -> DataQualityChecker:
    """
    Create a standard data quality checker with common rules.

    Returns:
        Configured DataQualityChecker
    """
    checker = DataQualityChecker()

    # Add common rules
    checker.add_rule(CompletenessRule(required_fields=["name", "url"]))

    # Add format rules
    def is_valid_url(value: Any) -> bool:
        """Check if value looks like a URL."""
        if not isinstance(value, str):
            return False
        return value.startswith("http://") or value.startswith("https://")

    checker.add_rule(FormatRule("url", is_valid_url))

    # Add range rules for common numeric fields
    checker.add_rule(RangeRule("price", min_value=0.0))
    checker.add_rule(RangeRule("rating", min_value=0.0, max_value=5.0))

    return checker
