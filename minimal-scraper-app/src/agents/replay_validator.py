# src/agents/replay_validator.py
from __future__ import annotations

from typing import Iterable, List

from src.common.logging_utils import get_logger

log = get_logger("replay-validator")


class ReplayFailure(Exception):
    """Raised when replay validation fails."""


def validate_replay_results(results: Iterable[bool]) -> None:
    res_list: List[bool] = list(results)
    if not res_list:
        log.warning("Replay validation called with no results")
        return
    failed = [r for r in res_list if not r]
    if failed:
        log.error("Replay validation failed (%d/%d failures)", len(failed), len(res_list))
        raise ReplayFailure(f"{len(failed)} replay checks failed out of {len(res_list)}")
    log.info("Replay validation succeeded (%d checks)", len(res_list))
