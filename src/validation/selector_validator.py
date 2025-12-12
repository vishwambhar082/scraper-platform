"""
Selector Validator Module

Validates CSS and XPath selectors for correctness and efficiency.
Provides recommendations for selector improvements.

Author: Scraper Platform Team
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SelectorType(str, Enum):
    """Types of selectors."""
    CSS = "css"
    XPATH = "xpath"
    UNKNOWN = "unknown"


class SelectorIssue(str, Enum):
    """Types of selector issues."""
    SYNTAX_ERROR = "syntax_error"
    INEFFICIENT = "inefficient"
    TOO_SPECIFIC = "too_specific"
    TOO_BROAD = "too_broad"
    FRAGILE = "fragile"
    DEPRECATED = "deprecated"


@dataclass
class SelectorValidationMessage:
    """Selector validation message."""

    issue_type: SelectorIssue
    severity: str  # "error", "warning", "info"
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion
        }


@dataclass
class SelectorValidationResult:
    """Result of selector validation."""

    selector: str
    selector_type: SelectorType
    is_valid: bool
    messages: List[SelectorValidationMessage] = field(default_factory=list)
    complexity_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "selector": self.selector,
            "selector_type": self.selector_type.value,
            "is_valid": self.is_valid,
            "complexity_score": self.complexity_score,
            "messages": [m.to_dict() for m in self.messages]
        }


class SelectorValidator:
    """
    Validates CSS and XPath selectors.

    Features:
    - Syntax validation
    - Performance analysis
    - Fragility detection
    - Best practice recommendations
    """

    # Patterns for fragile selectors
    FRAGILE_PATTERNS = {
        r'nth-child\(\d+\)': "Position-based selectors are fragile to DOM changes",
        r'nth-of-type\(\d+\)': "Position-based selectors are fragile to DOM changes",
        r'\[style.*\]': "Style-based selectors may break with CSS updates",
        r'#\w+\d{3,}': "Auto-generated IDs (with numbers) may change"
    }

    # Inefficient patterns
    INEFFICIENT_PATTERNS = {
        r'^\*': "Universal selector (*) at start is slow",
        r'\s+\*\s+': "Universal selector in middle position is slow",
        r'(\w+\s+){5,}': "Deep descendant selectors are slow"
    }

    def __init__(self):
        """Initialize selector validator."""
        logger.info("Initialized SelectorValidator")

    def validate(self, selector: str) -> SelectorValidationResult:
        """
        Validate a selector.

        Args:
            selector: CSS or XPath selector

        Returns:
            Validation result
        """
        logger.debug(f"Validating selector: {selector}")

        # Detect selector type
        selector_type = self._detect_type(selector)

        messages: List[SelectorValidationMessage] = []

        # Validate based on type
        if selector_type == SelectorType.CSS:
            messages.extend(self._validate_css(selector))
        elif selector_type == SelectorType.XPATH:
            messages.extend(self._validate_xpath(selector))
        else:
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.SYNTAX_ERROR,
                severity="error",
                message="Could not determine selector type (CSS or XPath)"
            ))

        # Calculate complexity
        complexity = self._calculate_complexity(selector, selector_type)

        # Check for errors
        has_errors = any(m.severity == "error" for m in messages)
        is_valid = not has_errors

        return SelectorValidationResult(
            selector=selector,
            selector_type=selector_type,
            is_valid=is_valid,
            messages=messages,
            complexity_score=complexity
        )

    def validate_batch(self, selectors: List[str]) -> Dict[str, SelectorValidationResult]:
        """
        Validate multiple selectors.

        Args:
            selectors: List of selectors to validate

        Returns:
            Dictionary mapping selectors to validation results
        """
        results = {}
        for selector in selectors:
            results[selector] = self.validate(selector)
        return results

    def _detect_type(self, selector: str) -> SelectorType:
        """Detect if selector is CSS or XPath."""
        if not selector:
            return SelectorType.UNKNOWN

        # XPath typically starts with / or // or contains XPath functions
        xpath_indicators = [
            selector.startswith('/'),
            selector.startswith('.//'),
            'text()' in selector,
            'contains(' in selector,
            'following-sibling' in selector,
            'preceding-sibling' in selector,
            'ancestor::' in selector,
            'descendant::' in selector
        ]

        if any(xpath_indicators):
            return SelectorType.XPATH

        # CSS indicators
        css_indicators = [
            '.' in selector,  # class
            '#' in selector,  # id
            '[' in selector,  # attribute
            '>' in selector,  # child combinator
            '~' in selector,  # sibling combinator
            '+' in selector,  # adjacent combinator
            ':' in selector   # pseudo-class
        ]

        if any(css_indicators) or selector.replace('-', '').replace('_', '').isalnum():
            return SelectorType.CSS

        return SelectorType.UNKNOWN

    def _validate_css(self, selector: str) -> List[SelectorValidationMessage]:
        """Validate CSS selector."""
        messages = []

        # Basic syntax check
        if not selector.strip():
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.SYNTAX_ERROR,
                severity="error",
                message="Selector is empty"
            ))
            return messages

        # Check for fragile patterns
        for pattern, warning in self.FRAGILE_PATTERNS.items():
            if re.search(pattern, selector):
                messages.append(SelectorValidationMessage(
                    issue_type=SelectorIssue.FRAGILE,
                    severity="warning",
                    message=warning,
                    suggestion="Use semantic classes or attributes instead"
                ))

        # Check for inefficient patterns
        for pattern, warning in self.INEFFICIENT_PATTERNS.items():
            if re.search(pattern, selector):
                messages.append(SelectorValidationMessage(
                    issue_type=SelectorIssue.INEFFICIENT,
                    severity="warning",
                    message=warning,
                    suggestion="Optimize selector for better performance"
                ))

        # Check complexity
        if selector.count(' ') > 5:
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.INEFFICIENT,
                severity="warning",
                message="Selector has too many levels (> 5)",
                suggestion="Simplify selector by using more specific classes"
            ))

        # Check for over-specification
        if selector.count('#') > 1:
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.TOO_SPECIFIC,
                severity="warning",
                message="Multiple IDs in selector (IDs should be unique)",
                suggestion="Use only one ID or switch to classes"
            ))

        return messages

    def _validate_xpath(self, selector: str) -> List[SelectorValidationMessage]:
        """Validate XPath selector."""
        messages = []

        # Basic syntax check
        if not selector.strip():
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.SYNTAX_ERROR,
                severity="error",
                message="Selector is empty"
            ))
            return messages

        # Check for common XPath issues
        if '//' in selector and selector.count('//') > 3:
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.INEFFICIENT,
                severity="warning",
                message="Too many '//' operators (slow performance)",
                suggestion="Use more specific path when possible"
            ))

        # Check for position-based selection
        if re.search(r'\[\d+\]', selector):
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.FRAGILE,
                severity="warning",
                message="Position-based selection is fragile",
                suggestion="Use attributes or text matching instead"
            ))

        # Check for text() without contains
        if 'text()=' in selector and 'contains' not in selector:
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.FRAGILE,
                severity="info",
                message="Exact text matching is fragile",
                suggestion="Consider using contains() for partial matching"
            ))

        # Check bracket balance
        open_brackets = selector.count('[')
        close_brackets = selector.count(']')
        if open_brackets != close_brackets:
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.SYNTAX_ERROR,
                severity="error",
                message="Unbalanced brackets in XPath"
            ))

        # Check parentheses balance
        open_parens = selector.count('(')
        close_parens = selector.count(')')
        if open_parens != close_parens:
            messages.append(SelectorValidationMessage(
                issue_type=SelectorIssue.SYNTAX_ERROR,
                severity="error",
                message="Unbalanced parentheses in XPath"
            ))

        return messages

    def _calculate_complexity(self, selector: str, selector_type: SelectorType) -> int:
        """
        Calculate selector complexity score (0-100).

        Lower is better.
        """
        score = 0

        # Base complexity on length
        score += min(len(selector) // 10, 20)

        # Add points for levels
        if selector_type == SelectorType.CSS:
            levels = selector.count(' ') + selector.count('>')
            score += levels * 5
        elif selector_type == SelectorType.XPATH:
            levels = selector.count('/')
            score += levels * 3

        # Add points for complex operators
        score += selector.count('*') * 10
        score += selector.count('[') * 2
        score += selector.count('::') * 3

        return min(score, 100)


def validate_selector(selector: str) -> SelectorValidationResult:
    """
    Convenience function to validate a selector.

    Args:
        selector: CSS or XPath selector

    Returns:
        Validation result
    """
    validator = SelectorValidator()
    return validator.validate(selector)
