# src/agents/proxy_optimizer.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ProxyStats:
    proxy_id: str
    success_count: int = 0
    failure_count: int = 0

    @property
    def total(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.success_count / self.total


def choose_best_proxy(stats: List[ProxyStats]) -> Optional[ProxyStats]:
    if not stats:
        return None
    return sorted(stats, key=lambda s: (s.success_rate, s.total), reverse=True)[0]


__all__ = ["ProxyStats", "choose_best_proxy"]
