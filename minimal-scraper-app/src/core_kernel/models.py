"""Shared data models for core pipeline payloads.

These Pydantic models formalize the main records passed between processors
and the execution engine so we can rely on static typing and validation.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RawRecord(BaseModel):
    """Representation of a raw scraped record before normalization.

    The model intentionally allows extra fields so scrapers can attach
    arbitrary metadata without breaking validation.
    """

    product_url: Optional[str] = Field(default=None, description="Canonical product URL if available.")
    item_url: Optional[str] = Field(default=None, description="Alternate URL key used by some scrapers.")
    url: Optional[str] = Field(default=None, description="Fallback URL field used by legacy pipelines.")
    name: Optional[str] = Field(default=None, description="Product display name as scraped.")
    price: Optional[float] = Field(default=None, description="Raw price value; may be string-coerced.")
    currency: Optional[str] = Field(default=None, description="Currency code for the scraped price.")
    company: Optional[str] = Field(default=None, description="Company or seller name associated with the listing.")
    source: Optional[str] = Field(default=None, description="Source identifier for the scraper run.")

    model_config = {
        "extra": "allow",
        "validate_assignment": True,
    }


class NormalizedRecord(BaseModel):
    """Normalized representation of a record ready for processing."""

    product_url: Optional[str] = Field(default=None, description="Canonical product URL.")
    name: Optional[str] = Field(default=None, description="Normalized product name.")
    price: Optional[float] = Field(default=None, description="Numeric price in the provided currency.")
    currency: str = Field(default="ARS", description="ISO currency code for the price.")
    company: Optional[str] = Field(default=None, description="Normalized company/seller name.")
    source: Optional[str] = Field(default=None, description="Source identifier for downstream auditing.")

    model_config = {
        "extra": "allow",
        "validate_assignment": True,
    }

    @classmethod
    def from_raw(cls, raw: RawRecord | dict[str, Any]) -> "NormalizedRecord":
        """Build a normalized record from raw scraper output.

        Args:
            raw: Raw record object or a dictionary of raw values.

        Returns:
            NormalizedRecord with canonical field names and parsed types.
        """

        raw_model = raw if isinstance(raw, RawRecord) else RawRecord.model_validate(raw)
        product_url = raw_model.product_url or raw_model.item_url or raw_model.url
        return cls(
            product_url=product_url,
            name=raw_model.name,
            price=raw_model.price,
            currency=raw_model.currency or "ARS",
            company=raw_model.company,
            source=raw_model.source,
        )


class PCIDMatchResult(BaseModel):
    """Match decision for a normalized record against a PCID index."""

    record: NormalizedRecord = Field(description="Normalized record that was evaluated.")
    pcid: Optional[str] = Field(default=None, description="Matched PCID, if any.")
    confidence: float = Field(default=0.0, description="Similarity or confidence score for the decision.")
    method: str = Field(default="exact", description="Matching strategy used (exact, vector, etc.).")

    model_config = {
        "extra": "allow",
        "validate_assignment": True,
    }
