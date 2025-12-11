# src/versioning/contract_validator.py
from __future__ import annotations

from typing import Dict, Any


class ContractViolation(Exception):
    """Raised when a record violates the declared data contract."""


def validate_record_against_contract(record: Dict[str, Any], contract: Dict[str, Any]) -> None:
    required = contract.get("required") or []
    missing = [f for f in required if f not in record or record[f] in (None, "")]
    if missing:
        raise ContractViolation(f"Missing required fields: {missing}")
