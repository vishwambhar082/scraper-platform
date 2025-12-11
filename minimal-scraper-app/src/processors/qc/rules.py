"""
QC rules: definitions + execution engine.

This module works at the *rule* level:
    - Define individual rules (required fields, price range, etc.)
    - Run a list of rules over a record
    - Produce per-rule results + overall pass/fail

High-level pipeline code should call:
    - run_qc_for_record(record, rules)
    - run_qc_batch(records, rules)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import validators


Record = Dict[str, Any]


@dataclass
class QCRuleResult:
    rule_id: str
    passed: bool
    severity: str  # "error" | "warning" | "info"
    message: str


@dataclass
class QCRule:
    rule_id: str
    description: str
    severity: str  # "error" | "warning" | "info"
    # Function that takes a record and returns (passed: bool, message: str)
    check_fn: Callable[[Record], Tuple[bool, str]]


def _rule_required_core_fields() -> QCRule:
    required = [
        "source",
        "country",
        "product_url",
        "name",
        "company",
        "price",
        "currency",
    ]

    def check(record: Record) -> Tuple[bool, str]:
        missing = validators.check_required_fields(record, required)
        if missing:
            return False, f"missing required fields: {', '.join(missing)}"
        return True, "all required fields present"

    return QCRule(
        rule_id="required_core_fields",
        description="Core source/country/url/name/company/price/currency must be present",
        severity="error",
        check_fn=check,
    )


def _rule_price_non_negative_and_sane() -> QCRule:
    def check(record: Record) -> Tuple[bool, str]:
        msg = validators.check_price_range(
            record,
            field="price",
            min_price=validators.Decimal("0.01"),
            max_price=validators.Decimal("1000000"),
        )
        if msg:
            return False, msg
        return True, "price within sane range"

    return QCRule(
        rule_id="price_sanity",
        description="Price must be non-negative and within a sane range",
        severity="error",
        check_fn=check,
    )


def _rule_currency_allowed() -> QCRule:
    def check(record: Record) -> Tuple[bool, str]:
        msg = validators.check_currency_allowed(record, field="currency")
        if msg:
            return False, msg
        return True, "currency allowed"

    return QCRule(
        rule_id="currency_allowed",
        description="Currency must be in allowed set",
        severity="error",
        check_fn=check,
    )


def _rule_reimbursed_leq_retail() -> QCRule:
    def check(record: Record) -> Tuple[bool, str]:
        msg = validators.check_reimbursed_leq_retail(
            record,
            reimbursed_field="reimbursed_price",
            retail_field="retail_price",
        )
        if msg:
            return False, msg
        return True, "reimbursed <= retail (or not applicable)"

    return QCRule(
        rule_id="reimbursed_leq_retail",
        description="Reimbursed price must be <= retail price when both present",
        severity="warning",
        check_fn=check,
    )


def get_default_ruleset(source: Optional[str] = None) -> List[QCRule]:
    """
    Return the default QC ruleset.

    You can later customize by source, e.g.:

        if source == "alfabeta":
            ...

    but for now we use a global ruleset.
    """
    rules: List[QCRule] = [
        _rule_required_core_fields(),
        _rule_price_non_negative_and_sane(),
        _rule_currency_allowed(),
        _rule_reimbursed_leq_retail(),
    ]
    return rules


def run_qc_for_record(
    record: Record,
    rules: Sequence[QCRule],
) -> Tuple[bool, List[QCRuleResult]]:
    """
    Run a list of QC rules on a single record.

    Returns:
        (overall_pass: bool, results: List[QCRuleResult])

    overall_pass is False if ANY rule with severity="error" fails.
    Warnings do not cause failure, but are reported.
    """
    results: List[QCRuleResult] = []
    has_error_failure = False

    for rule in rules:
        try:
            passed, msg = rule.check_fn(record)
        except Exception as exc:
            passed = False
            msg = f"rule execution error: {exc!r}"

        results.append(
            QCRuleResult(
                rule_id=rule.rule_id,
                passed=passed,
                severity=rule.severity,
                message=msg,
            )
        )

        if rule.severity == "error" and not passed:
            has_error_failure = True

    return (not has_error_failure), results


def run_qc_batch(
    records: Iterable[Record],
    rules: Optional[Sequence[QCRule]] = None,
    source: Optional[str] = None,
) -> Tuple[List[Record], List[Record], List[List[QCRuleResult]]]:
    """
    Batch wrapper over run_qc_for_record.

    Returns:
        (passed_records, failed_records, all_results)

    all_results is a list aligned with the original input order:
        all_results[i] → QC results for the i-th input record.
    """
    if rules is None:
        rules = get_default_ruleset(source=source)

    passed_records: List[Record] = []
    failed_records: List[Record] = []
    all_results: List[List[QCRuleResult]] = []

    for rec in records:
        ok, res = run_qc_for_record(rec, rules)
        all_results.append(res)
        if ok:
            passed_records.append(rec)
        else:
            failed_records.append(rec)

    return passed_records, failed_records, all_results
