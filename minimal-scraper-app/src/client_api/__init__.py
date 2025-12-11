"""Lightweight SDK for interacting with the scraper platform HTTP API.

The client_api package exists to give external orchestrators a typed, stable
interface for triggering scrapes and polling health/run metadata without
depending on the FastAPI internals. Clients wrap HTTP calls and return
pydantic models defined in :mod:`src.api.models` for consistency with the
backend responses.
"""

from .base import BaseAPIClient, ClientAPIError
from .scraping import ScraperClient
from .health import HealthClient

__all__ = [
    "BaseAPIClient",
    "ClientAPIError",
    "ScraperClient",
    "HealthClient",
]
