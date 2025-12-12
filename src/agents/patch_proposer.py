"""
Patch Proposer Module

Intelligently proposes selector patches based on DOM analysis, historical data,
and optionally LLM-based repair suggestions.

This module bridges between selector failure detection and automated repair,
providing multiple strategies for proposing selector fixes.

Author: Scraper Platform Team
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SelectorPatch:
    """
    Represents a proposed selector patch.

    Attributes:
        field_name: The field being patched
        old_selector: Current selector
        new_selector: Proposed new selector
        confidence: Confidence score (0.0 to 1.0)
        reason: Explanation of why this patch was proposed
        strategy: Strategy used to generate this patch
    """

    field_name: str
    old_selector: str
    new_selector: str
    confidence: float
    reason: str = ""
    strategy: str = "unknown"

    def is_valid(self) -> bool:
        """Check if patch is valid (confidence above threshold)."""
        return self.confidence >= 0.5 and self.new_selector != self.old_selector


@dataclass
class PatchProposalContext:
    """Context for patch proposal."""

    field_name: str
    old_selector: str
    old_html: Optional[str] = None
    new_html: Optional[str] = None
    error_message: Optional[str] = None
    historical_selectors: List[str] = field(default_factory=list)
    extracted_value: Optional[Any] = None


class PatchStrategy:
    """Base class for patch generation strategies."""

    def __init__(self, name: str):
        self.name = name

    def propose(self, context: PatchProposalContext) -> Optional[SelectorPatch]:
        """Propose a patch based on context."""
        raise NotImplementedError


class ClassNameEvolutionStrategy(PatchStrategy):
    """
    Detects class name changes and proposes updated selectors.

    Example: .product-card-v1 -> .product-card-v2
    """

    def __init__(self):
        super().__init__("class_evolution")

    def propose(self, context: PatchProposalContext) -> Optional[SelectorPatch]:
        """Propose patch based on class name evolution."""
        if not context.new_html or not context.old_selector:
            return None

        # Extract class names from old selector
        class_pattern = r"\.([a-zA-Z0-9_-]+)"
        old_classes = re.findall(class_pattern, context.old_selector)

        if not old_classes:
            return None

        # Look for similar class names in new HTML
        for old_class in old_classes:
            # Check for version increments: product-v1 -> product-v2
            version_match = re.match(r"(.+)-v(\d+)$", old_class)
            if version_match:
                base_name = version_match.group(1)
                old_version = int(version_match.group(2))

                # Try next version
                new_class = f"{base_name}-v{old_version + 1}"
                if new_class in context.new_html:
                    new_selector = context.old_selector.replace(f".{old_class}", f".{new_class}")
                    return SelectorPatch(
                        field_name=context.field_name,
                        old_selector=context.old_selector,
                        new_selector=new_selector,
                        confidence=0.85,
                        reason=f"Detected version evolution: {old_class} -> {new_class}",
                        strategy=self.name,
                    )

        return None


class AttributeSubstitutionStrategy(PatchStrategy):
    """
    Proposes using data attributes instead of classes when classes change.

    Example: .product-title -> [data-testid="product-title"]
    """

    def __init__(self):
        super().__init__("attribute_substitution")

    def propose(self, context: PatchProposalContext) -> Optional[SelectorPatch]:
        """Propose attribute-based selector."""
        if not context.new_html or not context.field_name:
            return None

        # Common attribute patterns to try
        attribute_patterns = [
            f'[data-testid="{context.field_name}"]',
            f'[data-test="{context.field_name}"]',
            f'[data-field="{context.field_name}"]',
            f'[id*="{context.field_name}"]',
            f'[class*="{context.field_name}"]',
        ]

        for attr_selector in attribute_patterns:
            if attr_selector in context.new_html or self._check_partial_match(attr_selector, context.new_html):
                return SelectorPatch(
                    field_name=context.field_name,
                    old_selector=context.old_selector,
                    new_selector=attr_selector,
                    confidence=0.75,
                    reason=f"Found stable attribute selector: {attr_selector}",
                    strategy=self.name,
                )

        return None

    def _check_partial_match(self, selector: str, html: str) -> bool:
        """Check if selector pattern exists in HTML."""
        # Extract attribute name and value
        match = re.search(r'\[([a-zA-Z-]+)[*=]+"([^"]+)"\]', selector)
        if match:
            attr_name = match.group(1)
            attr_value = match.group(2)
            return attr_name in html and attr_value in html
        return False


class StructurePreservationStrategy(PatchStrategy):
    """
    Maintains selector structure but updates specific parts.

    Example: div.card > h2.title -> div.card-new > h2.title-text
    """

    def __init__(self):
        super().__init__("structure_preservation")

    def propose(self, context: PatchProposalContext) -> Optional[SelectorPatch]:
        """Propose structure-preserving patch."""
        if not context.new_html or not context.old_selector:
            return None

        # If selector has hierarchy (contains >)
        if ">" in context.old_selector:
            parts = [p.strip() for p in context.old_selector.split(">")]

            # Try to find which part broke
            for i, part in enumerate(parts):
                if part not in context.new_html:
                    # Try to find similar element in new HTML
                    element_type = part.split(".")[0].split("[")[0]

                    # Look for same element type with different class
                    pattern = rf"{element_type}\.[a-zA-Z0-9_-]+"
                    matches = re.findall(pattern, context.new_html)

                    if matches:
                        # Use the first match
                        new_part = matches[0]
                        new_parts = parts.copy()
                        new_parts[i] = new_part
                        new_selector = " > ".join(new_parts)

                        return SelectorPatch(
                            field_name=context.field_name,
                            old_selector=context.old_selector,
                            new_selector=new_selector,
                            confidence=0.70,
                            reason=f"Updated part {i}: {part} -> {new_part}",
                            strategy=self.name,
                        )

        return None


class HistoricalPatternStrategy(PatchStrategy):
    """
    Uses historical selector changes to predict future patterns.

    Example: If field has changed from .title-v1 -> .title-v2 before,
    suggest .title-v3 when .title-v2 fails.
    """

    def __init__(self):
        super().__init__("historical_pattern")

    def propose(self, context: PatchProposalContext) -> Optional[SelectorPatch]:
        """Propose patch based on historical patterns."""
        if len(context.historical_selectors) < 2:
            return None

        # Analyze pattern in historical changes
        prev_selector = context.historical_selectors[-2]
        curr_selector = context.historical_selectors[-1]

        # Detect simple replacement pattern
        if len(prev_selector) == len(curr_selector):
            changes = []
            for i, (old_char, new_char) in enumerate(zip(prev_selector, curr_selector)):
                if old_char != new_char:
                    changes.append((i, old_char, new_char))

            # If pattern is simple (few changes), apply same transformation
            if 1 <= len(changes) <= 3:
                new_selector = list(curr_selector)
                for pos, old_char, new_char in changes:
                    # Simple increment if numeric
                    if old_char.isdigit() and new_char.isdigit():
                        next_digit = str(int(new_char) + 1)
                        new_selector[pos] = next_digit

                new_selector_str = "".join(new_selector)
                if new_selector_str != curr_selector:
                    return SelectorPatch(
                        field_name=context.field_name,
                        old_selector=context.old_selector,
                        new_selector=new_selector_str,
                        confidence=0.60,
                        reason="Applied historical pattern transformation",
                        strategy=self.name,
                    )

        return None


class XPathFallbackStrategy(PatchStrategy):
    """
    Proposes XPath selectors as a fallback when CSS selectors fail.

    XPath can be more robust for complex structures.
    """

    def __init__(self):
        super().__init__("xpath_fallback")

    def propose(self, context: PatchProposalContext) -> Optional[SelectorPatch]:
        """Propose XPath selector."""
        # Convert CSS to XPath approximation
        if not context.old_selector or context.old_selector.startswith("//"):
            return None  # Already XPath or invalid

        # Simple CSS to XPath conversion
        xpath = self._css_to_xpath(context.old_selector)

        if xpath and xpath != context.old_selector:
            return SelectorPatch(
                field_name=context.field_name,
                old_selector=context.old_selector,
                new_selector=xpath,
                confidence=0.55,
                reason="Converted to XPath for better stability",
                strategy=self.name,
            )

        return None

    def _css_to_xpath(self, css_selector: str) -> str:
        """Simple CSS to XPath conversion."""
        # Basic conversions
        xpath = css_selector

        # .class -> [contains(@class, 'class')]
        xpath = re.sub(r"\.([a-zA-Z0-9_-]+)", r"[contains(@class, '\1')]", xpath)

        # #id -> [@id='id']
        xpath = re.sub(r"#([a-zA-Z0-9_-]+)", r"[@id='\1']", xpath)

        # > -> /
        xpath = xpath.replace(" > ", "/")

        # element -> //element
        if not xpath.startswith("//"):
            xpath = "//" + xpath

        return xpath


class PatchProposer:
    """
    Main patch proposer that combines multiple strategies.

    Tries strategies in order of confidence and returns the best patch.
    """

    def __init__(self, strategies: Optional[List[PatchStrategy]] = None):
        """
        Initialize patch proposer.

        Args:
            strategies: List of strategies to use (default: all strategies)
        """
        if strategies is None:
            self.strategies = [
                ClassNameEvolutionStrategy(),
                AttributeSubstitutionStrategy(),
                StructurePreservationStrategy(),
                HistoricalPatternStrategy(),
                XPathFallbackStrategy(),
            ]
        else:
            self.strategies = strategies

        logger.info(f"Initialized PatchProposer with {len(self.strategies)} strategies")

    def propose_patches(self, context: PatchProposalContext, max_proposals: int = 3) -> List[SelectorPatch]:
        """
        Propose selector patches using multiple strategies.

        Args:
            context: Patch proposal context
            max_proposals: Maximum number of patches to return

        Returns:
            List of proposed patches, sorted by confidence
        """
        proposals: List[SelectorPatch] = []

        logger.info(f"Proposing patches for field: {context.field_name}")

        for strategy in self.strategies:
            try:
                patch = strategy.propose(context)
                if patch and patch.is_valid():
                    proposals.append(patch)
                    logger.debug(
                        f"Strategy '{strategy.name}' proposed: {patch.new_selector} "
                        f"(confidence: {patch.confidence:.2f})"
                    )
            except Exception as e:
                logger.warning(f"Strategy '{strategy.name}' failed: {e}")

        # Sort by confidence (descending)
        proposals.sort(key=lambda p: p.confidence, reverse=True)

        # Return top N proposals
        top_proposals = proposals[:max_proposals]
        logger.info(f"Generated {len(top_proposals)} patch proposals " f"(from {len(proposals)} total)")

        return top_proposals


# Convenience functions for backward compatibility


def propose_noop_patch(field_name: str, selector: str) -> SelectorPatch:
    """
    Minimal implementation: returns a "no-op" patch.

    Args:
        field_name: Field name
        selector: Current selector

    Returns:
        No-op patch (for testing)
    """
    return SelectorPatch(
        field_name=field_name,
        old_selector=selector,
        new_selector=selector,
        confidence=1.0,
        reason="No-op patch (testing)",
        strategy="noop",
    )


def propose_patch(
    field_name: str,
    old_selector: str,
    old_html: Optional[str] = None,
    new_html: Optional[str] = None,
    historical_selectors: Optional[List[str]] = None,
) -> Optional[SelectorPatch]:
    """
    Propose a single best patch for a selector.

    Args:
        field_name: Field name
        old_selector: Current selector
        old_html: Old HTML snapshot (optional)
        new_html: New HTML snapshot (optional)
        historical_selectors: Historical selector values (optional)

    Returns:
        Best proposed patch or None
    """
    context = PatchProposalContext(
        field_name=field_name,
        old_selector=old_selector,
        old_html=old_html,
        new_html=new_html,
        historical_selectors=historical_selectors or [],
    )

    proposer = PatchProposer()
    patches = proposer.propose_patches(context, max_proposals=1)

    return patches[0] if patches else None


__all__ = [
    "SelectorPatch",
    "PatchProposalContext",
    "PatchStrategy",
    "ClassNameEvolutionStrategy",
    "AttributeSubstitutionStrategy",
    "StructurePreservationStrategy",
    "HistoricalPatternStrategy",
    "XPathFallbackStrategy",
    "PatchProposer",
    "propose_noop_patch",
    "propose_patch",
]
