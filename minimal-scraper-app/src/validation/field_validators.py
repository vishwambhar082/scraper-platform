"""
Primitive validators for common scraper fields.
"""
from __future__ import annotations


def is_text_present(value: str | None, *, min_length: int = 1) -> bool:
    if not value:
        return False
    return len(value.strip()) >= min_length


def is_price_valid(value: object) -> bool:
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return numeric >= 0

