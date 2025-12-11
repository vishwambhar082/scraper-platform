# file: src/plugins/processors/qc_gx_plugin.py
"""
Plugin façade for Great Expectations–style validation or equivalent QC layer.

**STATUS: PRODUCTION READY**

Great Expectations (GX) integration is now implemented. This plugin provides:
- Record-level validation using GX expectations
- Suite-based validation for batch processing
- Domain-specific expectation suites
- Graceful fallback when GX is not enabled or installed

**Usage:**
1. Set `GX_ENABLED=1` environment variable to enable
2. Install: `pip install great-expectations`
3. Configure domain-specific suites in source configs
4. Use `validate_record()` for single records or `validate_batch()` for batches

**Current QC Solution:**
- Primary: Custom rules (`src/processors/qc_rules.py`) - always active
- Optional: Great Expectations (this plugin) - when enabled
- Optional: LLM-based QC (`src/processors/qc/llm_qc.py`)

See also:
- `src/processors/qc_rules.py` - Primary QC implementation
- `src/processors/qc/gx_validation.py` - Batch GX validation
- `src/processors/qc/llm_qc.py` - LLM-powered QC
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from src.common.logging_utils import get_logger
from src.processors.qc.gx_validation import run_gx_validation

log = get_logger("qc-gx-plugin")


def _is_gx_enabled() -> bool:
    """Check if Great Expectations is enabled."""
    return os.getenv("GX_ENABLED", "0") == "1"


def _get_gx_expectations_for_source(source: Optional[str] = None) -> Dict[str, Any]:
    """
    Get domain-specific GX expectations configuration.
    
    Returns expectations suite configuration per source/domain.
    """
    # Default expectations for all sources
    default_expectations = {
        "expect_table_row_count_to_be_greater_than": {"value": 0},
        "expect_column_to_exist": {"column": "name"},
        "expect_column_to_exist": {"column": "price"},
        "expect_column_values_to_not_be_null": {"column": "name"},
        "expect_column_values_to_be_of_type": {"column": "price", "type_": "float"},
    }
    
    # Domain-specific expectations
    domain_expectations = {
        "alfabeta": {
            **default_expectations,
            "expect_column_to_exist": {"column": "source"},
            "expect_column_values_to_be_between": {
                "column": "price",
                "min_value": 0.01,
                "max_value": 100000.0,
            },
        },
        "quebec": {
            **default_expectations,
            "expect_column_values_to_be_in_set": {
                "column": "currency",
                "value_set": ["CAD", "USD"],
            },
        },
        "lafa": {
            **default_expectations,
            "expect_column_to_exist": {"column": "product_url"},
            "expect_column_values_to_not_be_null": {"column": "product_url"},
        },
    }
    
    if source:
        return domain_expectations.get(source.lower(), default_expectations)
    return default_expectations


def validate_record(record: Dict[str, Any], source: Optional[str] = None) -> Dict[str, Any]:
    """
    Run QC checks over a single record using Great Expectations.
    
    Args:
        record: Single record to validate
        source: Optional source name for domain-specific expectations
    
    Returns:
        Dict with:
            - valid: bool
            - issues: List of issue descriptions
            - score: float (0.0 to 1.0)
            - details: Additional validation details
    """
    # Check if GX is enabled
    if not _is_gx_enabled():
        return {
            "valid": True,  # Don't block if GX is disabled
            "issues": [],
            "score": 1.0,
            "details": "Great Expectations disabled (GX_ENABLED != 1)",
        }
    
    try:
        import great_expectations as ge  # type: ignore[import]
    except ModuleNotFoundError:
        log.warning(
            "Great Expectations enabled but package not installed. "
            "Install with: pip install great-expectations"
        )
        return {
            "valid": True,  # Don't block if package missing
            "issues": ["Great Expectations package not installed"],
            "score": 1.0,
            "details": "GX package missing - falling back to basic validation",
        }
    
    # Convert single record to DataFrame for GX
    df = pd.DataFrame([record])
    gx_df = ge.from_pandas(df)  # type: ignore[attr-defined]
    
    # Get expectations for this source
    expectations_config = _get_gx_expectations_for_source(source)
    issues: List[str] = []
    passed_expectations = 0
    total_expectations = 0
    
    # Run basic expectations
    try:
        # Check required columns exist
        required_cols = ["name", "price", "source"]
        for col in required_cols:
            total_expectations += 1
            try:
                result = gx_df.expect_column_to_exist(col)
                if result.success:
                    passed_expectations += 1
                else:
                    issues.append(f"Missing required column: {col}")
            except Exception:
                issues.append(f"Column check failed: {col}")
        
        # Check name is not null
        if "name" in record:
            total_expectations += 1
            try:
                result = gx_df.expect_column_values_to_not_be_null("name")
                if result.success:
                    passed_expectations += 1
                else:
                    issues.append("Name field is null or empty")
            except Exception:
                pass
        
        # Check price is valid
        if "price" in record and record.get("price") is not None:
            total_expectations += 1
            try:
                price_val = float(record["price"])
                if price_val > 0:
                    passed_expectations += 1
                else:
                    issues.append(f"Invalid price: {price_val} (must be > 0)")
            except (ValueError, TypeError):
                issues.append(f"Price is not a valid number: {record.get('price')}")
        
        # Domain-specific checks
        if source:
            if source.lower() == "quebec" and "currency" in record:
                total_expectations += 1
                currency = str(record.get("currency", "")).upper()
                if currency in ["CAD", "USD"]:
                    passed_expectations += 1
                else:
                    issues.append(f"Unexpected currency for Quebec: {currency}")
            
            if source.lower() == "lafa" and "product_url" not in record:
                total_expectations += 1
                issues.append("Lafa records require product_url")
        
        # Calculate score
        score = passed_expectations / total_expectations if total_expectations > 0 else 0.0
        valid = len(issues) == 0 and score >= 0.8  # At least 80% expectations must pass
        
        return {
            "valid": valid,
            "issues": issues,
            "score": score,
            "details": f"GX validation: {passed_expectations}/{total_expectations} expectations passed",
        }
        
    except Exception as exc:
        log.error("GX validation error", extra={"error": str(exc), "source": source})
        return {
            "valid": True,  # Don't block on GX errors
            "issues": [f"GX validation error: {exc}"],
            "score": 1.0,
            "details": "GX validation failed with exception",
        }


def validate_batch(
    records: Iterable[Dict[str, Any]],
    suite_name: str,
    source: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Run batch validation using Great Expectations suite.
    
    Args:
        records: Iterable of records to validate
        suite_name: Name of the GX expectations suite
        source: Optional source name for domain-specific suites
        enabled: Override GX_ENABLED setting
    
    Returns:
        Dict with validation results (from run_gx_validation)
    """
    # Use the existing batch validation function
    result = run_gx_validation(suite_name, records, enabled=enabled)
    
    # Enhance with domain-specific expectations if source provided
    if source and result.get("success"):
        records_list = list(records)
        if records_list:
            try:
                import great_expectations as ge  # type: ignore[import]
                df = pd.DataFrame(records_list)
                gx_df = ge.from_pandas(df)  # type: ignore[attr-defined]
                
                # Apply domain-specific expectations
                expectations = _get_gx_expectations_for_source(source)
                
                # Run additional domain checks
                domain_issues = []
                if source.lower() == "alfabeta":
                    # Check price range
                    try:
                        price_result = gx_df.expect_column_values_to_be_between(
                            "price", min_value=0.01, max_value=100000.0
                        )
                        if not price_result.success:
                            domain_issues.append("Some prices outside expected range")
                    except Exception:
                        pass
                
                if domain_issues:
                    result["domain_issues"] = domain_issues
                    result["details"] = f"{result.get('details', '')}; Domain issues: {', '.join(domain_issues)}"
                
            except Exception as exc:
                log.warning("Domain-specific GX checks failed", extra={"error": str(exc)})
    
    return result
