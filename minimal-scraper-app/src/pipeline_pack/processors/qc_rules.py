from __future__ import annotations

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class QCRule:
    name: str = "base_rule"
    severity: str = "warning"

    def check(self, record: Dict[str, Any]) -> List[str]:
        raise NotImplementedError


class RequiredFieldRule(QCRule):
    def __init__(self, field: str):
        self.field = field
        self.name = f"required_{field}"

    def check(self, record: Dict[str, Any]) -> List[str]:
        if not record.get(self.field):
            return [f"{self.field} is required"]
        return []


class PositivePriceRule(QCRule):
    name = "positive_price"
    severity = "error"

    def check(self, record: Dict[str, Any]) -> List[str]:
        price = record.get("price")
        try:
            if price is None:
                return ["price is missing"]
            val = float(price)
            if val <= 0:
                return [f"price must be > 0, got {val}"]
        except (TypeError, ValueError):
            return [f"price not numeric: {price!r}"]
        return []


class QCRunner:
    def __init__(self, rules: List[QCRule]):
        self.rules = rules

    def run(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        error_count = 0
        warning_count = 0
        for idx, rec in enumerate(records):
            for rule in self.rules:
                msgs = rule.check(rec)
                for msg in msgs:
                    issue = {
                        "record_index": idx,
                        "rule": rule.name,
                        "severity": rule.severity,
                        "message": msg,
                    }
                    issues.append(issue)
                    if rule.severity == "error":
                        error_count += 1
                    else:
                        warning_count += 1
        return {
            "issues": issues,
            "error_count": error_count,
            "warning_count": warning_count,
        }


def default_qc_runner() -> QCRunner:
    rules: List[QCRule] = [
        RequiredFieldRule("product_name"),
        RequiredFieldRule("manufacturer"),
        PositivePriceRule(),
    ]
    return QCRunner(rules)


__all__ = [
    "QCRule",
    "RequiredFieldRule",
    "PositivePriceRule",
    "QCRunner",
    "default_qc_runner",
]
