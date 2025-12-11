"""
LLM-based field normalizer.

Uses LLM to normalize ambiguous text fields (product names, manufacturers, etc.).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.common.logging_utils import get_logger
from src.processors.llm.llm_client import LLMClient, get_llm_client_from_config

log = get_logger("llm-normalizer")


def normalize_field_with_llm(
    value: str,
    field_type: str,
    llm_client: LLMClient,
    examples: Optional[List[str]] = None,
) -> str:
    """
    Normalize a field value using LLM.

    Args:
        value: Raw value to normalize
        field_type: Type of field ('drug_name', 'manufacturer', 'pack_size', etc.)
        llm_client: LLM client instance
        examples: Optional examples of normalized values

    Returns:
        Normalized value
    """
    system_prompt = f"""You are a data normalization specialist. Normalize {field_type} values to canonical forms.

Rules:
- Remove extra whitespace
- Standardize abbreviations
- Fix common typos
- Use consistent casing
- Return only the normalized value, no explanation"""

    prompt = f"Normalize this {field_type} value: {value}"
    if examples:
        prompt += f"\n\nExamples of normalized values: {', '.join(examples)}"

    try:
        normalized = llm_client.complete(prompt, system_prompt=system_prompt)
        return normalized.strip()
    except Exception as exc:
        log.warning("LLM normalization failed, returning original", extra={"error": str(exc)})
        return value


def normalize_record_with_llm(
    record: Dict[str, Any],
    fields_to_normalize: List[str],
    llm_client: LLMClient,
    field_types: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Normalize multiple fields in a record using LLM.

    Args:
        record: Record dict
        fields_to_normalize: List of field names to normalize
        llm_client: LLM client instance
        field_types: Optional mapping of field names to types

    Returns:
        Record with normalized fields
    """
    field_types = field_types or {}
    normalized = record.copy()

    for field in fields_to_normalize:
        if field not in record:
            continue

        value = record[field]
        if not isinstance(value, str) or not value.strip():
            continue

        field_type = field_types.get(field, field)
        try:
            normalized[field] = normalize_field_with_llm(value, field_type, llm_client)
        except Exception as exc:
            log.warning(
                "Failed to normalize field",
                extra={"field": field, "error": str(exc)},
            )

    return normalized


def process_llm_normalization(
    records: Iterable[Dict[str, Any]],
    source_config: Dict[str, Any],
    fields_to_normalize: Optional[List[str]] = None,
) -> Iterable[Dict[str, Any]]:
    """
    Process records and normalize fields using LLM.

    Args:
        records: Records to normalize
        source_config: Source config with LLM settings
        fields_to_normalize: List of field names (if None, uses config)

    Yields:
        Normalized records
    """
    llm_config = source_config.get("llm", {})
    if not llm_config.get("enabled", False):
        # LLM disabled, pass through
        for record in records:
            yield record
        return

    llm_client = get_llm_client_from_config(source_config)
    if not llm_client:
        for record in records:
            yield record
        return

    # Get fields to normalize from config or parameter
    if fields_to_normalize is None:
        fields_to_normalize = llm_config.get("normalize_fields", [])

    if not fields_to_normalize:
        # Nothing to normalize
        for record in records:
            yield record
        return

    field_types = llm_config.get("field_types", {})

    for record in records:
        try:
            normalized = normalize_record_with_llm(
                record,
                fields_to_normalize,
                llm_client,
                field_types,
            )
            yield normalized
        except Exception as exc:
            log.error("LLM normalization failed for record", extra={"error": str(exc)})
            yield record  # Return original on error

