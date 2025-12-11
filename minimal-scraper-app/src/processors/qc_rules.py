from typing import Dict, Optional

from src.common.logging_utils import get_logger
from src.processors.qc.domain_validators import validate_by_domain

log = get_logger("qc-rules")


def is_valid(record: Dict, source: Optional[str] = None) -> bool:
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
        log.warning("Invalid record (no name): %s", record)
        return False
    price = record.get("price")
    if price is None or price <= 0:
        log.warning("Invalid record (bad price): %s", record)
        return False
    return True
