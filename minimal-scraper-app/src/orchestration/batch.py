"""
Batch orchestrator that triggers multiple sources sequentially.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from src.entrypoints.run_pipeline import run_pipeline


class BatchOrchestrator:
    def __init__(self, sources: Iterable[str]) -> None:
        self.sources = list(sources)

    def run(
        self,
        *,
        environment: str = "prod",
        run_type: str = "FULL_REFRESH",
        params: Optional[Dict[str, object]] = None,
    ) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        for source in self.sources:
            result = run_pipeline(
                source=source,
                run_type=run_type,
                environment=environment,
                params=params or {},
            )
            results.append(result)
        return results

