"""
Domain-specific QC validators.

Each domain (source type) can have custom validation rules.
"""

from typing import Dict, Any, List, Optional
from src.common.logging_utils import get_logger

log = get_logger("qc-domain-validators")


def validate_alfabeta(record: Dict[str, Any]) -> bool:
    """Alfabeta-specific validation rules."""
    # Required fields
    if not record.get("name"):
        log.warning("Alfabeta record missing name: %s", record.get("product_url"))
        return False
    
    if not record.get("price") or record.get("price", 0) <= 0:
        log.warning("Alfabeta record has invalid price: %s", record.get("product_url"))
        return False
    
    # Alfabeta-specific: should have company/lab name
    if not record.get("company") and not record.get("lab_name"):
        log.warning("Alfabeta record missing company/lab_name: %s", record.get("product_url"))
        # Not fatal, but logged
    
    # Alfabeta-specific: presentation field should exist for pharmaceuticals
    if record.get("category") == "pharmaceutical" and not record.get("presentation"):
        log.warning("Pharmaceutical product missing presentation: %s", record.get("product_url"))
        # Not fatal
    
    return True


def validate_quebec(record: Dict[str, Any]) -> bool:
    """Quebec-specific validation rules."""
    # Required fields
    if not record.get("name"):
        log.warning("Quebec record missing name: %s", record.get("product_url"))
        return False
    
    if not record.get("price") or record.get("price", 0) <= 0:
        log.warning("Quebec record has invalid price: %s", record.get("product_url"))
        return False
    
    # Quebec-specific: currency should be CAD or USD
    currency = record.get("currency", "").upper()
    if currency and currency not in ["CAD", "USD"]:
        log.warning("Quebec record has unexpected currency: %s (expected CAD or USD)", currency)
        # Not fatal, but logged
    
    # Quebec-specific: price range validation (reasonable for Canadian market)
    price = record.get("price", 0)
    if price > 100000:
        log.warning("Quebec record has unusually high price: %s", price)
        # Not fatal, but logged
    
    # Quebec-specific: should have source field
    if not record.get("source"):
        log.warning("Quebec record missing source field")
        # Not fatal
    
    return True


def validate_lafa(record: Dict[str, Any]) -> bool:
    """Lafa-specific validation rules."""
    # Required fields
    if not record.get("name"):
        log.warning("Lafa record missing name: %s", record.get("product_url"))
        return False
    
    if not record.get("price") or record.get("price", 0) <= 0:
        log.warning("Lafa record has invalid price: %s", record.get("product_url"))
        return False
    
    # Lafa-specific: should have source URL (required)
    if not record.get("product_url") and not record.get("item_url"):
        log.warning("Lafa record missing URL: %s", record)
        return False
    
    # Lafa-specific: URL should be valid
    url = record.get("product_url") or record.get("item_url", "")
    if url and not (url.startswith("http://") or url.startswith("https://")):
        log.warning("Lafa record has invalid URL format: %s", url)
        # Not fatal, but logged
    
    # Lafa-specific: should have source field
    if not record.get("source"):
        log.warning("Lafa record missing source field")
        # Not fatal
    
    return True


def validate_template(record: Dict[str, Any]) -> bool:
    """Template/default validation rules."""
    # Basic validation for template/unknown sources
    if not record.get("name"):
        log.warning("Template record missing name: %s", record.get("product_url"))
        return False
    
    if not record.get("price") or record.get("price", 0) <= 0:
        log.warning("Template record has invalid price: %s", record.get("product_url"))
        return False
    
    # Template: should have source field
    if not record.get("source"):
        log.warning("Template record missing source field")
        # Not fatal, but recommended
    
    return True


def validate_chile(record: Dict[str, Any]) -> bool:
    """Chile-specific validation rules."""
    # Required fields
    if not record.get("name"):
        log.warning("Chile record missing name: %s", record.get("product_url"))
        return False
    
    if not record.get("price") or record.get("price", 0) <= 0:
        log.warning("Chile record has invalid price: %s", record.get("product_url"))
        return False
    
    # Chile-specific: currency should be CLP (Chilean Peso) or USD
    currency = record.get("currency", "").upper()
    if currency and currency not in ["CLP", "USD"]:
        log.warning("Chile record has unexpected currency: %s (expected CLP or USD)", currency)
        # Not fatal
    
    # Chile-specific: price range validation
    price = record.get("price", 0)
    if currency == "CLP" and price > 10000000:  # 10M CLP is very high
        log.warning("Chile record has unusually high price in CLP: %s", price)
        # Not fatal
    
    return True


def validate_argentina(record: Dict[str, Any]) -> bool:
    """Argentina-specific validation rules."""
    # Required fields
    if not record.get("name"):
        log.warning("Argentina record missing name: %s", record.get("product_url"))
        return False
    
    if not record.get("price") or record.get("price", 0) <= 0:
        log.warning("Argentina record has invalid price: %s", record.get("product_url"))
        return False
    
    # Argentina-specific: currency should be ARS (Argentine Peso) or USD
    currency = record.get("currency", "").upper()
    if currency and currency not in ["ARS", "USD"]:
        log.warning("Argentina record has unexpected currency: %s (expected ARS or USD)", currency)
        # Not fatal
    
    # Argentina-specific: should have company/lab name (similar to Alfabeta)
    if not record.get("company") and not record.get("lab_name"):
        log.warning("Argentina record missing company/lab_name: %s", record.get("product_url"))
        # Not fatal, but recommended
    
    return True


# Domain validator registry
DOMAIN_VALIDATORS: Dict[str, callable] = {
    "alfabeta": validate_alfabeta,
    "quebec": validate_quebec,
    "lafa": validate_lafa,
    "template": validate_template,
    "chile": validate_chile,
    "argentina": validate_argentina,
}


def validate_by_domain(record: Dict[str, Any], source: Optional[str] = None) -> bool:
    """
    Validate a record using domain-specific rules.
    
    Args:
        record: Record to validate
        source: Source name (e.g., "alfabeta", "quebec")
    
    Returns:
        True if valid, False otherwise
    """
    # Extract source from record if not provided
    if not source:
        source = record.get("source", "template")
    
    # Get domain validator
    validator = DOMAIN_VALIDATORS.get(source.lower(), validate_template)
    
    try:
        return validator(record)
    except Exception as exc:
        log.error("Domain validator failed for source=%s: %s", source, exc)
        # Fallback to basic validation
        return validate_template(record)


def get_domain_requirements(source: str) -> Dict[str, Any]:
    """
    Get required fields and validation rules for a domain.
    
    Returns:
        Dict with 'required_fields', 'optional_fields', 'validation_rules'
    """
    requirements = {
        "alfabeta": {
            "required_fields": ["name", "price", "source"],
            "optional_fields": ["company", "lab_name", "presentation", "pcid"],
            "validation_rules": [
                "price > 0",
                "name not empty",
                "company or lab_name recommended",
            ],
        },
        "quebec": {
            "required_fields": ["name", "price", "source"],
            "optional_fields": ["currency", "product_url"],
            "validation_rules": [
                "price > 0",
                "currency should be CAD or USD",
            ],
        },
        "lafa": {
            "required_fields": ["name", "price", "source", "product_url"],
            "optional_fields": ["currency", "company"],
            "validation_rules": [
                "price > 0",
                "product_url required",
            ],
        },
        "template": {
            "required_fields": ["name", "price", "source"],
            "optional_fields": ["product_url", "currency", "company"],
            "validation_rules": [
                "price > 0",
                "name not empty",
            ],
        },
        "chile": {
            "required_fields": ["name", "price", "source"],
            "optional_fields": ["currency", "product_url", "company"],
            "validation_rules": [
                "price > 0",
                "currency should be CLP or USD",
                "name not empty",
            ],
        },
        "argentina": {
            "required_fields": ["name", "price", "source"],
            "optional_fields": ["company", "lab_name", "currency", "product_url"],
            "validation_rules": [
                "price > 0",
                "currency should be ARS or USD",
                "company or lab_name recommended",
            ],
        },
    }
    
    return requirements.get(source.lower(), requirements["template"])

