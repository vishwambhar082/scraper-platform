"""
LLM-based quality control.

Uses LLM to validate records, detect anomalies, and flag issues.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.common.logging_utils import get_logger
from src.processors.llm.llm_client import LLMClient, get_llm_client_from_config

log = get_logger("llm-qc")


def validate_record_with_llm(
    record: Dict[str, Any],
    required_fields: List[str],
    llm_client: LLMClient,
    validation_rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate a record using LLM.

    Args:
        record: Record to validate
        required_fields: List of required field names
        llm_client: LLM client instance
        validation_rules: Optional validation rules (e.g., price ranges)

    Returns:
        Dict with:
            - valid: bool
            - issues: List of issue descriptions
            - score: float (0.0 to 1.0)
    """
    # Check required fields first (fast)
    missing_fields = [f for f in required_fields if not record.get(f)]
    if missing_fields:
        return {
            "valid": False,
            "issues": [f"Missing required fields: {', '.join(missing_fields)}"],
            "score": 0.0,
        }

    # Build validation prompt
    system_prompt = """You are a data quality validator. Analyze records and identify issues.

Check for:
- Missing or null required fields
- Invalid data types
- Suspicious values (e.g., prices that are too high/low)
- Inconsistent data
- Duplicate indicators

Return JSON with: {"valid": bool, "issues": [str], "score": float}"""

    record_str = "\n".join(f"{k}: {v}" for k, v in record.items() if v is not None)
    prompt = f"""Validate this record:

{record_str}

Required fields: {', '.join(required_fields)}
"""

    if validation_rules:
        prompt += f"\nValidation rules: {validation_rules}"

    try:
        result = llm_client.extract_json(prompt, system_prompt=system_prompt)
        if isinstance(result, dict):
            return {
                "valid": result.get("valid", True),
                "issues": result.get("issues", []),
                "score": float(result.get("score", 1.0)),
            }
        else:
            return {"valid": True, "issues": [], "score": 1.0}
    except Exception as exc:
        log.warning("LLM validation failed, assuming valid", extra={"error": str(exc)})
        return {"valid": True, "issues": [], "score": 1.0}


def process_llm_qc(
    records: Iterable[Dict[str, Any]],
    source_config: Dict[str, Any],
    required_fields: Optional[List[str]] = None,
) -> Iterable[Dict[str, Any]]:
    """
    Process records and perform LLM-based QC.

    Args:
        records: Records to validate
        source_config: Source config with LLM settings
        required_fields: List of required fields (if None, uses config)

    Yields:
        Records with '_qc_llm' field added
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

    # Get required fields from config or parameter
    if required_fields is None:
        required_fields = source_config.get("quality", {}).get("required_fields", [])

    validation_rules = source_config.get("quality", {}).get("validation_rules", {})

    for record in records:
        try:
            qc_result = validate_record_with_llm(
                record,
                required_fields or [],
                llm_client,
                validation_rules,
            )
            record["_qc_llm"] = qc_result
            record["_qc_valid"] = qc_result["valid"]
            record["_qc_score"] = qc_result["score"]
            if qc_result["issues"]:
                record["_qc_issues"] = qc_result["issues"]
        except Exception as exc:
            log.error("LLM QC failed for record", extra={"error": str(exc)})
            record["_qc_llm"] = {"valid": True, "issues": [], "score": 1.0}
            record["_qc_valid"] = True

        yield record

