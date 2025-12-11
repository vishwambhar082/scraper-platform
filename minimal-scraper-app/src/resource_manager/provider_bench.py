"""
Benchmark proxy or browser providers to pick the fastest option.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable


@dataclass
class ProviderResult:
    name: str
    latency_ms: float
    success_rate: float


class ProviderBench:
    def __init__(self, providers: Dict[str, Callable[[], bool]]) -> None:
        self.providers = providers

    def run(self, samples: int = 3) -> Iterable[ProviderResult]:
        for name, callable_ in self.providers.items():
            latencies = []
            successes = 0
            for _ in range(samples):
                start = time.perf_counter()
                try:
                    ok = callable_()
                    successes += int(ok)
                except Exception:
                    ok = False
                finally:
                    latencies.append((time.perf_counter() - start) * 1000)
            yield ProviderResult(
                name=name,
                latency_ms=statistics.mean(latencies),
                success_rate=successes / samples,
            )

