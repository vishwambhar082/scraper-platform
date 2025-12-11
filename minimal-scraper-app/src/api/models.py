from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class RunStep(APIModel):
    id: str
    name: str
    status: str
    startedAt: datetime
    durationSeconds: Optional[int] = None


class RunSummary(APIModel):
    id: str
    source: str
    status: str
    startedAt: datetime
    durationSeconds: Optional[int] = None
    variantId: Optional[str] = None


class RunDetail(RunSummary):
    finishedAt: Optional[datetime] = None
    stats: Dict[str, Any] = Field(default_factory=dict)
    steps: List[RunStep] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VariantBenchmark(APIModel):
    variantId: str
    totalRuns: int
    successRate: float
    dataCompleteness: float
    costPerRecord: float
    totalRecords: int


class SourceHealth(APIModel):
    source: str
    status: str
    lastRunAt: Optional[datetime] = None
    lastSuccessAt: Optional[datetime] = None
    consecutiveFailures: int = 0
    budgetExhausted: bool = False
