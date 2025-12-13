"""
Shared type aliases/dataclasses.

Migrated from deleted src.core_kernel.models module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel
except ImportError:
    # Fallback if pydantic not available
    BaseModel = object  # type: ignore


@dataclass
class RunMetadata:
    run_id: str
    source: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    extra: Dict[str, object]


# Product/record models (migrated from core_kernel)
class NormalizedRecord(BaseModel):
    """Normalized product record with validated fields."""
    product_url: Optional[str] = None
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    strength: Optional[str] = None
    pack_size: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"  # Allow additional fields


class RawRecord(BaseModel):
    """Raw scraped record before normalization."""
    url: Optional[str] = None
    html: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class PCIDMatchResult(BaseModel):
    """Result of PCID matching operation."""
    pcid: Optional[str] = None
    match_score: float = 0.0
    matched_fields: Dict[str, Any] = {}

    class Config:
        extra = "allow"

