"""
Factory for creating QC services with default configurations.
"""

from typing import List, Optional
from src.processors.qc.application.service import QCService
from src.processors.qc.domain.rules import QCConfiguration
from src.processors.qc.infrastructure.validators import (
    RequiredFieldsValidator,
    PriceRangeValidator,
    CurrencyValidator,
    ReimbursementValidator
)


def create_default_qc_service(source: Optional[str] = None, config: Optional[QCConfiguration] = None) -> QCService:
    """
    Create a QC service with default validators.
    
    Args:
        source: Optional source identifier for source-specific rules
        config: Optional configuration for the QC service
        
    Returns:
        Configured QCService instance
    """
    # Core required fields for all sources
    core_fields = [
        "source",
        "country",
        "product_url",
        "name",
        "company",
        "price",
        "currency",
    ]
    
    # Create default validators
    validators = [
        RequiredFieldsValidator(core_fields, "required_core_fields"),
        PriceRangeValidator(),
        CurrencyValidator(),
        ReimbursementValidator(),
    ]
    
    # Source-specific validators could be added here
    # if source == "specific_source":
    #     validators.append(SpecificSourceValidator())
    
    return QCService(validators=validators, config=config)


def create_custom_qc_service(validators: List, config: Optional[QCConfiguration] = None) -> QCService:
    """
    Create a QC service with custom validators.
    
    Args:
        validators: List of QCRecordValidator instances
        config: Optional configuration for the QC service
        
    Returns:
        Configured QCService instance
    """
    return QCService(validators=validators, config=config)