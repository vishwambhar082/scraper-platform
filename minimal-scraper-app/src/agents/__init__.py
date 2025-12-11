from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from src.common.logging_utils import get_logger

from .agent_framework import (
    AgentContext,
    AgentOrchestrator,
    AgentRegistry,
    AgentResult,
    BaseAgent,
    ReplayValidationAgent,
    SelectorRepairAgent,
    VolumeDriftAgent,
    build_example_news_pipeline,
)
from .llm import NoOpLLM
from .patch_proposer import SelectorPatch, propose_noop_patch
from .replay_validator import ReplayFailure, validate_replay_results
from .scraper_brain import ScraperAssessment, assess_source_health
from .selector_diff_utils import SelectorDiff, diff_selectors

log = get_logger("agents")


@dataclass
class AgenticReport:
    source: str
    health: Optional[ScraperAssessment]
    selector_diffs: List[SelectorDiff] = field(default_factory=list)
    proposed_patches: Dict[str, SelectorPatch] = field(default_factory=dict)
    replay_ok: bool = True
    errors: List[str] = field(default_factory=list)
    llm_summary: Optional[str] = None


def run_agentic_check(
    source: str,
    baseline_rows: int = 0,
    current_rows: int = 0,
    selectors_before: Optional[Dict[str, Any]] = None,
    selectors_after: Optional[Dict[str, Any]] = None,
    replay_results: Optional[Iterable[bool]] = None,
    llm: Optional[NoOpLLM] = None,
) -> AgenticReport:
    """
    Run lightweight agentic sanity checks for a scraper source.

    The implementation intentionally avoids network calls or LLM invocations so
    that it can be executed safely in constrained environments.
    """

    errors: List[str] = []

    health: Optional[ScraperAssessment]
    try:
        health = assess_source_health(source, baseline_rows, current_rows)
    except Exception as exc:  # noqa: BLE001
        log.error("Health assessment failed for %s: %s", source, exc)
        errors.append(f"health:{exc}")
        health = None

    selector_diffs: List[SelectorDiff] = []
    if selectors_before is not None and selectors_after is not None:
        try:
            selector_diffs = diff_selectors(selectors_before, selectors_after)
        except Exception as exc:  # noqa: BLE001
            log.error("Selector diffing failed for %s: %s", source, exc)
            errors.append(f"selectors:{exc}")

    proposed_patches: Dict[str, SelectorPatch] = {}
    for diff in selector_diffs:
        proposed_patches[diff.field] = propose_noop_patch(diff.field, str(diff.new))

    llm_summary: Optional[str] = None
    llm_backend = llm or NoOpLLM()
    if selector_diffs:
        try:
            prompts = [f"{d.field}: {d.old} -> {d.new}" for d in selector_diffs]
            llm_summary = llm_backend.generate(prompts)
        except Exception as exc:  # noqa: BLE001
            log.error("LLM summary generation failed for %s: %s", source, exc)
            errors.append(f"llm:{exc}")

    replay_ok = True
    if replay_results is not None:
        try:
            validate_replay_results(replay_results)
        except ReplayFailure as exc:
            replay_ok = False
            errors.append(f"replay:{exc}")
        except Exception as exc:  # noqa: BLE001
            replay_ok = False
            errors.append(f"replay:{exc}")

    return AgenticReport(
        source=source,
        health=health,
        selector_diffs=selector_diffs,
        proposed_patches=proposed_patches,
        replay_ok=replay_ok,
        errors=errors,
        llm_summary=llm_summary,
    )


__all__ = [
    "AgenticReport",
    "run_agentic_check",
    "ScraperAssessment",
    "SelectorPatch",
    "SelectorDiff",
    "NoOpLLM",
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "AgentRegistry",
    "AgentOrchestrator",
    "VolumeDriftAgent",
    "SelectorRepairAgent",
    "ReplayValidationAgent",
    "build_example_news_pipeline",
]
