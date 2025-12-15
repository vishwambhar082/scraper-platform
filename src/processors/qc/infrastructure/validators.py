"""
Infrastructure implementations of QC validators.

This module contains concrete implementations of QC validators
that depend on external libraries or specific business logic.
"""

from decimal import Decimal, InvalidOperation
from typing import List, Optional, Sequence, Set
from src.processors.qc.domain.rules import (
    QCRecordValidator, 
    QCRuleResult, 
    Record, 
    SeverityLevel
)


def get_numeric(record: Record, key: str) -> Optional[Decimal]:
    """Safely parse a numeric field from a record; returns None if missing/invalid."""
    value = record.get(key)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def check_required_fields(record: Record, fields: Sequence[str]) -> List[str]:
    """
    Return list of missing or empty field names.
    
    Empty strings and None are treated as missing.
    """
    missing: List[str] = []
    for f in fields:
        v = record.get(f)
        if v is None:
            missing.append(f)
        elif isinstance(v, str) and not v.strip():
            missing.append(f)
    return missing


def check_price_range(
    record: Record,
    field: str,
    min_price: Decimal,
    max_price: Decimal,
) -> Optional[str]:
    """
    Check that price is within a sane range.
    
    Returns an error message string if invalid, otherwise None.
    """
    raw_val = record.get(field)
    val = get_numeric(record, field)
    if raw_val is not None and val is None:
        return f"{field} is not a valid number"

    if val is None:
        # let required-field rules handle missing
        return None
    if val < min_price:
        return f"{field}={val} is below minimum {min_price}"
    if val > max_price:
        return f"{field}={val} is above maximum {max_price}"
    return None


def check_currency_allowed(
    record: Record,
    field: str = "currency",
    allowed: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """
    Ensure currency is in the allowed set.
    
    Returns an error message string if invalid, otherwise None.
    """
    if allowed is None:
        allowed_set: Set[str] = {"ARS", "USD", "EUR"}
    else:
        allowed_set = {c.upper() for c in allowed}

    cur = record.get(field)
    if cur is None:
        return None  # let required rules handle missing if needed

    cur_str = str(cur).upper().strip()
    if cur_str not in allowed_set:
        return f"{field}={cur_str} is not in allowed set {sorted(allowed_set)}"
    return None


def check_reimbursed_leq_retail(
    record: Record,
    reimbursed_field: str = "reimbursed_price",
    retail_field: str = "retail_price",
) -> Optional[str]:
    """
    Ensure reimbursed price is <= retail price if both present.
    
    Returns an error message string if invalid, otherwise None.
    """
    reimbursed = get_numeric(record, reimbursed_field)
    retail = get_numeric(record, retail_field)

    if reimbursed is None or retail is None:
        return None

    if reimbursed > retail:
        return (
            f"{reimbursed_field}={reimbursed} is greater than "
            f"{retail_field}={retail}"
        )
    return None


class RequiredFieldsValidator(QCRecordValidator):
    """Validator for required fields."""
    
    def __init__(self, fields: Sequence[str], rule_id: str = "required_fields"):
        self.fields = list(fields)
        self.rule_id = rule_id
        self.description = f"Required fields must be present: {', '.join(fields)}"
    
    def validate(self, record: Record) -> QCRuleResult:
        missing = check_required_fields(record, self.fields)
        if missing:
            return QCRuleResult(
                rule_id=self.rule_id,
                passed=False,
                severity=SeverityLevel.ERROR,
                message=f"missing required fields: {', '.join(missing)}"
            )
        return QCRuleResult(
            rule_id=self.rule_id,
            passed=True,
            severity=SeverityLevel.INFO,
            message="all required fields present"
        )


class PriceRangeValidator(QCRecordValidator):
    """Validator for price range checks."""
    
    def __init__(
        self, 
        field: str = "price",
        min_price: Decimal = Decimal("0.01"),
        max_price: Decimal = Decimal("1000000"),
        rule_id: str = "price_sanity"
    ):
        self.field = field
        self.min_price = min_price
        self.max_price = max_price
        self.rule_id = rule_id
        self.description = f"Price must be between {min_price} and {max_price}"
    
    def validate(self, record: Record) -> QCRuleResult:
        msg = check_price_range(record, self.field, self.min_price, self.max_price)
        if msg:
            return QCRuleResult(
                rule_id=self.rule_id,
                passed=False,
                severity=SeverityLevel.ERROR,
                message=msg
            )
        return QCRuleResult(
            rule_id=self.rule_id,
            passed=True,
            severity=SeverityLevel.INFO,
            message="price within sane range"
        )


class CurrencyValidator(QCRecordValidator):
    """Validator for currency checks."""
    
    def __init__(
        self, 
        field: str = "currency",
        allowed_currencies: Optional[Sequence[str]] = None,
        rule_id: str = "currency_allowed"
    ):
        self.field = field
        self.allowed_currencies = allowed_currencies
        self.rule_id = rule_id
        currencies = allowed_currencies or ["ARS", "USD", "EUR"]
        self.description = f"Currency must be one of: {', '.join(currencies)}"
    
    def validate(self, record: Record) -> QCRuleResult:
        msg = check_currency_allowed(record, self.field, self.allowed_currencies)
        if msg:
            return QCRuleResult(
                rule_id=self.rule_id,
                passed=False,
                severity=SeverityLevel.ERROR,
                message=msg
            )
        return QCRuleResult(
            rule_id=self.rule_id,
            passed=True,
            severity=SeverityLevel.INFO,
            message="currency allowed"
        )


class ReimbursementValidator(QCRecordValidator):
    """Validator for reimbursement price checks."""
    
    def __init__(
        self,
        reimbursed_field: str = "reimbursed_price",
        retail_field: str = "retail_price",
        rule_id: str = "reimbursed_leq_retail"
    ):
        self.reimbursed_field = reimbursed_field
        self.retail_field = retail_field
        self.rule_id = rule_id
        self.description = "Reimbursed price must be <= retail price when both present"
    
    def validate(self, record: Record) -> QCRuleResult:
        msg = check_reimbursed_leq_retail(record, self.reimbursed_field, self.retail_field)
        if msg:
            return QCRuleResult(
                rule_id=self.rule_id,
                passed=False,
                severity=SeverityLevel.WARNING,
                message=msg
            )
        return QCRuleResult(
            rule_id=self.rule_id,
            passed=True,
            severity=SeverityLevel.INFO,
            message="reimbursed <= retail (or not applicable)"
        )