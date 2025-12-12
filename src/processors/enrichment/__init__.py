"""
Enrichment Processors Module

This module provides data enrichment processors that augment scraped data
with additional information from external sources.

Available Enrichers:
- GeoEnricher: Adds geographic information (coordinates, regions, etc.)
- APIEnricher: Enriches data using third-party APIs
"""

from typing import List

__all__: List[str] = [
    "geo_enricher",
    "api_enricher",
]
