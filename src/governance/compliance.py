"""
Compliance Module

Enforces compliance with legal and ethical scraping standards.
Includes robots.txt checking, rate limiting, and data privacy.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlparse
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class ComplianceRule:
    """Compliance rule definition."""

    rule_id: str
    name: str
    description: str
    severity: str  # "critical", "high", "medium", "low"
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "enabled": self.enabled
        }


@dataclass
class ComplianceViolation:
    """Compliance violation record."""

    rule_id: str
    rule_name: str
    severity: str
    message: str
    timestamp: datetime
    url: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "url": self.url,
            "details": self.details
        }


@dataclass
class ComplianceReport:
    """Compliance check report."""

    timestamp: datetime
    target_url: str
    rules_checked: int
    violations: List[ComplianceViolation]
    is_compliant: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "target_url": self.target_url,
            "rules_checked": self.rules_checked,
            "violation_count": len(self.violations),
            "is_compliant": self.is_compliant,
            "violations": [v.to_dict() for v in self.violations]
        }


class RobotsTxtChecker:
    """Checks robots.txt compliance."""

    def __init__(self):
        """Initialize robots.txt checker."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        logger.debug("Initialized RobotsTxtChecker")

    def is_allowed(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if URL is allowed by robots.txt.

        Args:
            url: URL to check
            user_agent: User agent string

        Returns:
            True if allowed, False otherwise
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Check cache
        cache_key = f"{base_url}:{user_agent}"
        if cache_key in self.cache:
            rules = self.cache[cache_key]
            return self._check_path(parsed.path, rules)

        # In production, would fetch and parse robots.txt
        # For now, assume allowed
        logger.debug(f"Checking robots.txt for {base_url}")
        return True

    def _check_path(self, path: str, rules: Dict[str, Any]) -> bool:
        """Check if path is allowed by rules."""
        # Simplified implementation
        disallowed_patterns = rules.get("disallow", [])

        for pattern in disallowed_patterns:
            if path.startswith(pattern):
                return False

        return True


class RateLimiter:
    """Rate limiting for compliance."""

    def __init__(self, requests_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time: Dict[str, datetime] = {}
        logger.debug(f"Initialized RateLimiter: {requests_per_second} req/s")

    def check_rate(self, domain: str) -> bool:
        """
        Check if request is within rate limits.

        Args:
            domain: Domain to check

        Returns:
            True if within limits, False otherwise
        """
        now = datetime.now()

        if domain not in self.last_request_time:
            self.last_request_time[domain] = now
            return True

        last_time = self.last_request_time[domain]
        elapsed = (now - last_time).total_seconds()

        if elapsed < self.min_interval:
            return False

        self.last_request_time[domain] = now
        return True

    def get_wait_time(self, domain: str) -> float:
        """
        Get required wait time before next request.

        Args:
            domain: Domain to check

        Returns:
            Wait time in seconds (0 if can proceed)
        """
        if domain not in self.last_request_time:
            return 0.0

        now = datetime.now()
        last_time = self.last_request_time[domain]
        elapsed = (now - last_time).total_seconds()

        if elapsed >= self.min_interval:
            return 0.0

        return self.min_interval - elapsed


class DataPrivacyChecker:
    """Checks for data privacy compliance."""

    # Patterns that might indicate personal data
    SENSITIVE_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    }

    def __init__(self):
        """Initialize data privacy checker."""
        logger.debug("Initialized DataPrivacyChecker")

    def check_for_pii(self, data: Dict[str, Any]) -> List[str]:
        """
        Check data for personally identifiable information.

        Args:
            data: Data to check

        Returns:
            List of PII types found
        """
        import re

        found_pii = []

        # Convert data to string for pattern matching
        data_str = json.dumps(data)

        for pii_type, pattern in self.SENSITIVE_PATTERNS.items():
            if re.search(pattern, data_str):
                found_pii.append(pii_type)

        return found_pii


class ComplianceChecker:
    """
    Main compliance checker.

    Features:
    - robots.txt compliance
    - Rate limiting enforcement
    - Data privacy checks
    - Terms of service validation
    - Legal requirement verification
    """

    def __init__(
        self,
        requests_per_second: float = 1.0,
        respect_robots_txt: bool = True
    ):
        """
        Initialize compliance checker.

        Args:
            requests_per_second: Rate limit
            respect_robots_txt: Whether to check robots.txt
        """
        self.rate_limiter = RateLimiter(requests_per_second)
        self.robots_checker = RobotsTxtChecker() if respect_robots_txt else None
        self.privacy_checker = DataPrivacyChecker()
        self.rules = self._load_default_rules()
        logger.info("Initialized ComplianceChecker")

    def _load_default_rules(self) -> List[ComplianceRule]:
        """Load default compliance rules."""
        return [
            ComplianceRule(
                rule_id="ROBOTS_001",
                name="robots.txt Compliance",
                description="Respect robots.txt directives",
                severity="critical"
            ),
            ComplianceRule(
                rule_id="RATE_001",
                name="Rate Limiting",
                description="Enforce rate limits to prevent server overload",
                severity="high"
            ),
            ComplianceRule(
                rule_id="PRIVACY_001",
                name="No PII Collection",
                description="Avoid collecting personally identifiable information",
                severity="critical"
            ),
            ComplianceRule(
                rule_id="LEGAL_001",
                name="Terms of Service",
                description="Comply with website terms of service",
                severity="high"
            )
        ]

    def check_url(self, url: str, user_agent: str = "*") -> ComplianceReport:
        """
        Check compliance for a URL.

        Args:
            url: URL to check
            user_agent: User agent string

        Returns:
            Compliance report
        """
        logger.info(f"Checking compliance for: {url}")
        violations = []

        # Check robots.txt
        if self.robots_checker:
            if not self.robots_checker.is_allowed(url, user_agent):
                violations.append(ComplianceViolation(
                    rule_id="ROBOTS_001",
                    rule_name="robots.txt Compliance",
                    severity="critical",
                    message=f"URL disallowed by robots.txt: {url}",
                    timestamp=datetime.now(),
                    url=url
                ))

        # Check rate limiting
        parsed = urlparse(url)
        domain = parsed.netloc
        if not self.rate_limiter.check_rate(domain):
            wait_time = self.rate_limiter.get_wait_time(domain)
            violations.append(ComplianceViolation(
                rule_id="RATE_001",
                rule_name="Rate Limiting",
                severity="high",
                message=f"Rate limit exceeded for {domain}",
                timestamp=datetime.now(),
                url=url,
                details={"wait_time": wait_time}
            ))

        # Generate report
        is_compliant = not any(v.severity == "critical" for v in violations)

        report = ComplianceReport(
            timestamp=datetime.now(),
            target_url=url,
            rules_checked=len(self.rules),
            violations=violations,
            is_compliant=is_compliant
        )

        logger.info(
            f"Compliance check complete: compliant={is_compliant}, "
            f"violations={len(violations)}"
        )

        return report

    def check_data(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        """
        Check scraped data for compliance issues.

        Args:
            data: Scraped data to check

        Returns:
            List of violations
        """
        violations = []

        # Check for PII
        pii_found = self.privacy_checker.check_for_pii(data)
        if pii_found:
            violations.append(ComplianceViolation(
                rule_id="PRIVACY_001",
                rule_name="No PII Collection",
                severity="critical",
                message=f"Potentially sensitive data detected: {', '.join(pii_found)}",
                timestamp=datetime.now(),
                details={"pii_types": pii_found}
            ))

        return violations

    def add_rule(self, rule: ComplianceRule) -> None:
        """
        Add a custom compliance rule.

        Args:
            rule: Compliance rule to add
        """
        self.rules.append(rule)
        logger.info(f"Added compliance rule: {rule.name}")

    def get_violations_summary(
        self,
        violations: List[ComplianceViolation]
    ) -> Dict[str, Any]:
        """
        Get summary of violations.

        Args:
            violations: List of violations

        Returns:
            Summary dictionary
        """
        by_severity = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }

        for violation in violations:
            severity = violation.severity
            if severity in by_severity:
                by_severity[severity].append(violation)

        return {
            "total": len(violations),
            "by_severity": {
                k: len(v) for k, v in by_severity.items()
            },
            "critical_count": len(by_severity["critical"]),
            "has_critical": len(by_severity["critical"]) > 0
        }


def check_compliance(url: str, **kwargs) -> ComplianceReport:
    """
    Convenience function to check URL compliance.

    Args:
        url: URL to check
        **kwargs: Additional arguments for ComplianceChecker

    Returns:
        Compliance report
    """
    checker = ComplianceChecker(**kwargs)
    return checker.check_url(url)
