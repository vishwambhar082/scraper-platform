"""
Statistics Module

Provides statistical analysis and metrics for scraper runs.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RunStatistics:
    """Statistics for scraper runs."""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    avg_duration: float = 0.0
    total_records: int = 0

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100


class StatsCollector:
    """Collects and calculates statistics."""

    def __init__(self):
        """Initialize stats collector."""
        self.runs: List[Dict[str, Any]] = []
        logger.info("Initialized StatsCollector")

    def add_run(self, run_data: Dict[str, Any]) -> None:
        """Add run data for analysis."""
        self.runs.append(run_data)

    def calculate_stats(self) -> RunStatistics:
        """Calculate statistics from collected runs."""
        if not self.runs:
            return RunStatistics()

        total = len(self.runs)
        successful = sum(1 for r in self.runs if r.get("status") == "success")
        failed = total - successful

        total_duration = sum(r.get("duration", 0) for r in self.runs)
        avg_duration = total_duration / total if total > 0 else 0

        total_records = sum(r.get("record_count", 0) for r in self.runs)

        return RunStatistics(
            total_runs=total,
            successful_runs=successful,
            failed_runs=failed,
            avg_duration=avg_duration,
            total_records=total_records
        )
