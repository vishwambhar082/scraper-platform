"""
Run Optimizer Module

Optimizes scraper run scheduling based on historical performance,
resource availability, and business priorities.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OptimizationStrategy(str, Enum):
    """Optimization strategies."""
    COST = "cost"
    SPEED = "speed"
    RELIABILITY = "reliability"
    BALANCED = "balanced"


@dataclass
class RunProfile:
    """Profile of a scraper run."""

    scraper_name: str
    avg_duration: float
    success_rate: float
    avg_cost: float
    resource_usage: Dict[str, float]


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation."""

    scraper_name: str
    recommended_time: datetime
    estimated_duration: float
    estimated_cost: float
    confidence: float
    reasoning: str


class RunOptimizer:
    """
    Optimizes scraper run scheduling.

    Features:
    - Historical analysis
    - Resource-aware scheduling
    - Cost optimization
    - Performance prediction
    """

    def __init__(self, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED):
        """
        Initialize run optimizer.

        Args:
            strategy: Optimization strategy
        """
        self.strategy = strategy
        self.profiles: Dict[str, RunProfile] = {}
        logger.info(f"Initialized RunOptimizer with strategy: {strategy.value}")

    def analyze_run_history(self, scraper_name: str, runs: List[Dict[str, Any]]) -> RunProfile:
        """
        Analyze historical run data.

        Args:
            scraper_name: Scraper name
            runs: List of historical runs

        Returns:
            Run profile
        """
        if not runs:
            return RunProfile(
                scraper_name=scraper_name,
                avg_duration=0.0,
                success_rate=0.0,
                avg_cost=0.0,
                resource_usage={}
            )

        total_duration = sum(r.get('duration', 0) for r in runs)
        success_count = sum(1 for r in runs if r.get('status') == 'success')
        total_cost = sum(r.get('cost', 0) for r in runs)

        profile = RunProfile(
            scraper_name=scraper_name,
            avg_duration=total_duration / len(runs),
            success_rate=success_count / len(runs),
            avg_cost=total_cost / len(runs),
            resource_usage={}
        )

        self.profiles[scraper_name] = profile
        return profile

    def recommend_run_time(
        self,
        scraper_name: str,
        earliest: Optional[datetime] = None,
        latest: Optional[datetime] = None
    ) -> OptimizationRecommendation:
        """
        Recommend optimal run time.

        Args:
            scraper_name: Scraper name
            earliest: Earliest allowed time
            latest: Latest allowed time

        Returns:
            Optimization recommendation
        """
        profile = self.profiles.get(scraper_name)

        if not profile:
            # No history, recommend now
            return OptimizationRecommendation(
                scraper_name=scraper_name,
                recommended_time=datetime.now(),
                estimated_duration=300.0,  # Default 5 min
                estimated_cost=1.0,
                confidence=0.0,
                reasoning="No historical data available"
            )

        # Calculate optimal time based on strategy
        if self.strategy == OptimizationStrategy.COST:
            recommended_time = self._optimize_for_cost(earliest or datetime.now())
        elif self.strategy == OptimizationStrategy.SPEED:
            recommended_time = earliest or datetime.now()
        else:
            recommended_time = datetime.now() + timedelta(minutes=5)

        return OptimizationRecommendation(
            scraper_name=scraper_name,
            recommended_time=recommended_time,
            estimated_duration=profile.avg_duration,
            estimated_cost=profile.avg_cost,
            confidence=profile.success_rate,
            reasoning=f"Based on {self.strategy.value} optimization"
        )

    def _optimize_for_cost(self, earliest: datetime) -> datetime:
        """Optimize for minimum cost (off-peak hours)."""
        # Schedule for off-peak (e.g., night hours)
        target = earliest.replace(hour=2, minute=0, second=0)
        if target < earliest:
            target += timedelta(days=1)
        return target

    def get_recommendations(
        self,
        scraper_names: List[str],
        time_window: timedelta = timedelta(hours=24)
    ) -> List[OptimizationRecommendation]:
        """Get recommendations for multiple scrapers."""
        recommendations = []
        start_time = datetime.now()

        for name in scraper_names:
            rec = self.recommend_run_time(
                name,
                earliest=start_time,
                latest=start_time + time_window
            )
            recommendations.append(rec)

        return recommendations
