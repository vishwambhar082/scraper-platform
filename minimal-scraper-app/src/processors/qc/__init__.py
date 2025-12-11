"""
Quality Control Module.

This module provides functionality for validating data quality in scraped records.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple
from src.processors.qc.domain.rules import QCConfiguration, Record
from src.processors.qc.factory import create_default_qc_service

# For backward compatibility
def is_valid(record: Dict[str, Any], source: Optional[str] = None) -> bool:
    """
    Validate a record against quality control rules.
    
    Uses domain-specific validators when available, falls back to basic validation.
    
    Args:
        record: Record to validate
        source: Optional source name for domain-specific validation
    
    Returns:
        True if valid, False otherwise
    """
    # Use domain-specific validation if source is provided
    if source:
        return validate_by_domain(record, source)
    
    # Fallback to basic validation
    if not record.get("name"):
        return False
    price = record.get("price")
    if price is None or price <= 0:
        return False
    return True


def validate_by_domain(record: Record, source: str) -> bool:
    """
    Validate a record using domain-specific requirements.
    
    Args:
        record: Record to validate
        source: Source name for domain-specific validation
        
    Returns:
        True if valid, False otherwise
    """
    # Get domain-specific requirements
    requirements = _get_domain_requirements(source)
    required_fields = requirements.get("required_fields", [])
    
    # Check required fields
    for field in required_fields:
        if not record.get(field):
            return False
    
    # Check price if present
    price = record.get("price")
    if price is not None:
        try:
            price_val = float(price)
            if price_val <= 0:
                return False
        except (ValueError, TypeError):
            return False
    
    return True


def _get_domain_requirements(source: str) -> Dict[str, List[str]]:
    """
    Get domain-specific requirements for validation.
    
    Args:
        source: Source name
        
    Returns:
        Dictionary with validation requirements
    """
    requirements = {
        "alfabeta": {
            "required_fields": ["name", "price", "source"],
        },
        "quebec": {
            "required_fields": ["name", "price", "source"],
        },
        "lafa": {
            "required_fields": ["name", "price", "source", "product_url"],
        },
        "template": {
            "required_fields": ["name", "price", "source"],
        },
        "chile": {
            "required_fields": ["name", "price", "source"],
        },
        "argentina": {
            "required_fields": ["name", "price", "source"],
        },
    }
    
    return requirements.get(source.lower(), requirements["template"])


def run_qc_for_record(
    record: Record,
    rules=None,  # For backward compatibility, not used in new implementation
    source: Optional[str] = None
) -> Tuple[bool, List]:
    """
    Run QC validation on a single record.
    
    Args:
        record: Record to validate
        rules: Not used (kept for backward compatibility)
        source: Optional source for domain-specific validation
        
    Returns:
        Tuple of (passed, results)
    """
    service = create_default_qc_service(source=source)
    passed, results = service.validate_record(record)
    
    # Convert to backward compatible format
    converted_results = []
    for result in results:
        converted_results.append({
            'rule_id': result.rule_id,
            'passed': result.passed,
            'severity': result.severity.value,
            'message': result.message
        })
    
    return passed, converted_results


def run_qc_batch(
    records: Sequence[Record],
    rules=None,  # For backward compatibility, not used in new implementation
    source: Optional[str] = None
) -> Tuple[List[Record], List[Record], List[List]]:
    """
    Run QC validation on a batch of records.
    
    Args:
        records: Records to validate
        rules: Not used (kept for backward compatibility)
        source: Optional source for domain-specific validation
        
    Returns:
        Tuple of (passed_records, failed_records, all_results)
    """
    service = create_default_qc_service(source=source)
    passed_records, failed_records, all_results = service.validate_batch(records)
    
    # Convert to backward compatible format
    converted_all_results = []
    for results in all_results:
        converted_results = []
        for result in results:
            converted_results.append({
                'rule_id': result.rule_id,
                'passed': result.passed,
                'severity': result.severity.value,
                'message': result.message
            })
        converted_all_results.append(converted_results)
    
    return passed_records, failed_records, converted_all_results


# Backward compatibility exports
__all__ = [
    "is_valid",
    "run_qc_for_record",
    "run_qc_batch",
    "validate_by_domain"
]