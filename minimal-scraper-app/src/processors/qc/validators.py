"""
Low-level validation helpers used by QC rules.

These functions are deliberately dumb and deterministic: they only know how
to look at a single record and check basic conditions.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Set


Record = Dict[str, Any]


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


def check_non_negative_fields(record: Record, fields: Sequence[str]) -> List[str]:
    """
    Return list of fields that are negative (i.e. < 0).
    Missing or non-parsable fields are ignored here.
    """
    bad: List[str] = []
    for f in fields:
        val = get_numeric(record, f)
        if val is not None and val < 0:
            bad.append(f)
    return bad


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
    allowed: Optional[Iterable[str]] = None,
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


def build_dedupe_key(
    record: Record,
    fields: Sequence[str],
) -> Tuple[Any, ...]:
    """
    Build a hashable dedupe key from selected fields.

    Missing fields become None; strings are normalized (strip + lower).
    """
    key_parts: List[Any] = []
    for f in fields:
        v = record.get(f)
        if isinstance(v, str):
            key_parts.append(v.strip().lower())
        else:
            key_parts.append(v)
    return tuple(key_parts)
