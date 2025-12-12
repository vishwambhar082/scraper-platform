"""
LLM-based selector engine.

Uses LLM to automatically detect CSS/XPath selectors from HTML
and extract structured fields. This is the "Auto-Selector Engine" feature.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.common.config_loader import load_source_config as _load_source_config
from src.common.logging_utils import get_logger
from src.processors.llm.llm_client import LLMClient, get_llm_client_from_config

log = get_logger("llm-selector-engine")


def load_source_config(source: str) -> dict:
    """Thin wrapper so tests can patch source config loading."""

    return _load_source_config(source)


def extract_selectors_with_llm(
    html: str,
    fields: List[str],
    llm_client: LLMClient,
    existing_selectors: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Extract CSS/XPath selectors from HTML using LLM.

    Args:
        html: HTML content to analyze
        fields: List of field names to extract (e.g., ["price", "title", "pack"])
        llm_client: LLM client instance
        existing_selectors: Optional existing selectors to use as hints

    Returns:
        Dict mapping field names to CSS/XPath selectors
    """
    system_prompt = """You are a web scraping expert. Analyze HTML and generate CSS or XPath selectors
to extract specific fields. Return only valid selectors that uniquely identify each field.

Return JSON with field names as keys and selectors as values.
Use CSS selectors when possible, XPath only when necessary."""

    fields_str = ", ".join(fields)
    prompt = f"""Analyze this HTML and generate selectors for these fields: {fields_str}

HTML:
{html[:10000]}  # Limit HTML size for token efficiency

Return JSON like:
{{
  "price": "css selector or xpath",
  "title": "css selector or xpath",
  ...
}}"""

    if existing_selectors:
        prompt += f"\n\nExisting selectors (may be broken, use as hints):\n{existing_selectors}"

    try:
        result = llm_client.extract_json(prompt, system_prompt=system_prompt)
        if isinstance(result, dict):
            return result
        else:
            log.warning("LLM returned non-dict for selectors", extra={"result_type": type(result)})
            return {}
    except Exception as exc:
        log.error("Failed to extract selectors with LLM", extra={"error": str(exc)})
        return {}


def extract_fields_with_llm(
    html: str,
    fields: List[str],
    llm_client: LLMClient,
    selectors: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Extract structured fields directly from HTML using LLM.

    This is an alternative to selector-based extraction - LLM reads HTML directly.

    Args:
        html: HTML content
        fields: List of field names to extract
        llm_client: LLM client instance
        selectors: Optional selectors to focus LLM on specific sections

    Returns:
        Dict with extracted field values
    """
    system_prompt = """You are a data extraction specialist. Extract structured data from HTML.
Return only the extracted values as JSON, no explanation."""

    fields_str = ", ".join(fields)

    # If selectors provided, extract those sections first
    if selectors:
        # This is a simplified version - in production you'd extract HTML sections
        # using the selectors first, then pass to LLM
        prompt = f"""Extract these fields from the HTML: {fields_str}

HTML:
{html[:8000]}

Return JSON with field names as keys and extracted values as values."""
    else:
        prompt = f"""Extract these fields from the HTML: {fields_str}

HTML:
{html[:8000]}

Return JSON with field names as keys and extracted values as values."""

    try:
        result = llm_client.extract_json(prompt, system_prompt=system_prompt)
        if isinstance(result, dict):
            return result
        else:
            log.warning("LLM returned non-dict for fields", extra={"result_type": type(result)})
            return {}
    except Exception as exc:
        log.error("Failed to extract fields with LLM", extra={"error": str(exc)})
        return {}


def repair_selectors_with_llm(
    html_old: str,
    html_new: str,
    old_selectors: Dict[str, str],
    fields: List[str],
    llm_client: LLMClient,
) -> Dict[str, str]:
    """
    Repair broken selectors by comparing old and new HTML.

    Args:
        html_old: Previous HTML (when selectors worked)
        html_new: Current HTML (where selectors broke)
        old_selectors: Selectors that no longer work
        fields: Field names to extract
        llm_client: LLM client instance

    Returns:
        Updated selectors that work with new HTML
    """
    system_prompt = """You are a web scraping expert. Selectors that worked on old HTML are broken on new HTML.
Analyze both HTML versions and generate new selectors that work with the new HTML.

Return JSON with field names as keys and new selectors as values."""

    fields_str = ", ".join(fields)
    prompt = f"""Old HTML (selectors worked):
{html_old[:5000]}

New HTML (selectors broken):
{html_new[:5000]}

Old selectors:
{old_selectors}

Fields to extract: {fields_str}

Generate new selectors that work with the new HTML.
Return JSON with field names as keys and new selectors as values."""

    try:
        result = llm_client.extract_json(prompt, system_prompt=system_prompt)
        if isinstance(result, dict):
            return result
        else:
            log.warning("LLM returned non-dict for repaired selectors")
            return old_selectors  # Fallback to old selectors
    except Exception as exc:
        log.error("Failed to repair selectors with LLM", extra={"error": str(exc)})
        return old_selectors  # Fallback to old selectors


def auto_extract_with_llm(
    html: str,
    source_config: Dict[str, Any],
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    High-level function: automatically extract fields from HTML using LLM.

    This is the main entry point for LLM-based extraction.

    Args:
        html: HTML content
        source_config: Source config with LLM settings
        fields: Fields to extract (if None, uses config)

    Returns:
        Dict with extracted field values
    """
    llm_config = source_config.get("llm", {})
    if not llm_config.get("enabled", False):
        log.warning("LLM not enabled for this source")
        return {}

    llm_client = get_llm_client_from_config(source_config)
    if not llm_client:
        log.warning("LLM client not available")
        return {}

    if fields is None:
        # Get fields from config or use defaults
        fields = source_config.get("extract_fields", ["name", "price", "description"])

    # Check if we should use selector-based or direct extraction
    mode = source_config.get("mode", {}).get("extract_engine", "classic")

    if mode == "llm":
        # Direct LLM extraction (no selectors)
        return extract_fields_with_llm(html, fields, llm_client)
    else:
        # Generate selectors first, then extract
        selectors = extract_selectors_with_llm(html, fields, llm_client)
        if selectors:
            # Use selectors to extract (classic way) or pass to LLM
            return extract_fields_with_llm(html, fields, llm_client, selectors=selectors)
        else:
            # Fallback to direct extraction
            return extract_fields_with_llm(html, fields, llm_client)
