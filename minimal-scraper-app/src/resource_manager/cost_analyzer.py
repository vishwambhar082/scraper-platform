"""
Cost analyzer aggregating proxy/browser spend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CostAnalyzer:
    proxy_costs: Dict[str, float] = field(default_factory=dict)
    browser_costs: Dict[str, float] = field(default_factory=dict)

    def record_proxy_cost(self, source: str, amount: float) -> None:
        self.proxy_costs[source] = self.proxy_costs.get(source, 0.0) + amount

    def record_browser_cost(self, source: str, amount: float) -> None:
        self.browser_costs[source] = self.browser_costs.get(source, 0.0) + amount

    def summarize(self) -> Dict[str, float]:
        summary = {}
        for source, amount in self.proxy_costs.items():
            summary[source] = summary.get(source, 0.0) + amount
        for source, amount in self.browser_costs.items():
            summary[source] = summary.get(source, 0.0) + amount
        return summary

