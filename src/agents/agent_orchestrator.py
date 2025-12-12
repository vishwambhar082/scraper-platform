"""Agent orchestrator wiring for self-healing runs.

This module connects the lightweight agent helpers (drift detection,
selector repair, replay validation) into a single callable that can be
invoked from DAGs or pipelines when volume/QC drops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from src.agents.deepagent_repair_engine import run_repair_session
from src.agents.replay_validator import ReplayFailure, validate_replay_results
from src.agents.scraper_brain import ScraperAssessment, assess_source_health
from src.common.logging_utils import get_logger
from src.common.paths import OUTPUT_DIR

log = get_logger("agent-orchestrator")


@dataclass
class AgenticOutcome:
    """Summarizes actions performed by the orchestrator."""

    source: str
    assessment: ScraperAssessment
    triggered_repair: bool = False
    replay_validated: bool = False
    notes: List[str] = field(default_factory=list)


def _read_row_count(csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    try:
        # Skip header line
        return max(sum(1 for _ in csv_path.open("r", encoding="utf-8")) - 1, 0)
    except OSError:
        return 0


def load_recent_output_counts(source: str, limit: int = 2) -> List[int]:
    """Return most recent row counts for a source's daily CSVs."""

    daily_dir = OUTPUT_DIR / source / "daily"
    if not daily_dir.exists():
        return []

    csvs = sorted(daily_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    counts: List[int] = []
    for csv_path in csvs[:limit]:
        counts.append(_read_row_count(csv_path))
    return counts


def orchestrate_source_repair(
    source: str,
    baseline_rows: int,
    current_rows: int,
    validation_rate: Optional[float] = None,
    selectors_path: Optional[Path] = None,
    replay_results: Optional[Iterable[bool]] = None,
) -> AgenticOutcome:
    """Run drift/anomaly checks and trigger repairs when warranted."""

    assessment = assess_source_health(source, baseline_rows, current_rows)
    outcome = AgenticOutcome(source=source, assessment=assessment)

    qc_degraded = validation_rate is not None and validation_rate < 0.9
    if qc_degraded:
        outcome.notes.append(f"QC degraded: validation_rate={validation_rate:.3f}")

    if assessment.drift_decision.action != "noop" or assessment.has_volume_anomaly or qc_degraded:
        patches = run_repair_session(source, selectors_path=selectors_path)
        outcome.triggered_repair = bool(patches)
        outcome.notes.append(f"repair_session={'triggered' if patches else 'no_patches'}")  # type: ignore[str-format]

    if replay_results is not None:
        try:
            validate_replay_results(replay_results)
            outcome.replay_validated = True
        except ReplayFailure as exc:
            outcome.notes.append(f"replay_validation_failed: {exc}")

    log.info(
        "Agentic orchestrator completed for %s (drift_action=%s, qc_degraded=%s, repair=%s)",
        source,
        assessment.drift_decision.action,
        qc_degraded,
        outcome.triggered_repair,
    )
    return outcome


__all__ = [
    "AgenticOutcome",
    "load_recent_output_counts",
    "orchestrate_source_repair",
    "run_auto_heal",
]


def run_auto_heal(run_id: str, source_name: str, *, dry_run: bool = True) -> AgenticOutcome:
    """Convenience wrapper to trigger the orchestrator for a single source.

    This keeps the signature stable for callers that only know the run_id and
    source name. We derive basic volume stats from recent outputs to decide
    whether to trigger repairs.
    """

    counts = load_recent_output_counts(source_name, limit=2)
    current_rows = counts[0] if counts else 0
    baseline_rows = counts[1] if len(counts) > 1 else current_rows

    outcome = orchestrate_source_repair(
        source=source_name,
        baseline_rows=baseline_rows,
        current_rows=current_rows,
    )

    if dry_run and outcome.triggered_repair:
        outcome.notes.append("dry_run: repair simulated only")
        outcome.triggered_repair = False

    log.info("Auto-heal completed for run %s (source=%s)", run_id, source_name)
    return outcome
