# src/observability/synthetic_checks.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional
from src.common.logging_utils import get_logger

log = get_logger("synthetic-checks")

@dataclass
class SyntheticCheckResult:
    ok: bool
    error: Optional[str] = None

def run_login_check(source: str, check_fn: Callable[[], bool]) -> SyntheticCheckResult:
    try:
        ok = check_fn()
        if ok:
            log.info("Synthetic login check OK for %s", source)
            return SyntheticCheckResult(ok=True)
        log.warning("Synthetic login check FAILED for %s", source)
        return SyntheticCheckResult(ok=False, error="check_fn returned False")
    except Exception as exc:
        log.error("Synthetic login check ERROR for %s: %s", source, exc)
        return SyntheticCheckResult(ok=False, error=str(exc))
