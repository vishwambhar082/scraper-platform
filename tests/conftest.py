"""Pytest configuration and fixtures."""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip tests that require PostgreSQL when DB_URL is not set."""
    if not os.getenv("DB_URL"):
        skip_db = pytest.mark.skip(reason="PostgreSQL not available (DB_URL not set)")
        for item in items:
            # Skip run_tracking tests that require PostgreSQL-specific features
            if "test_run_tracking" in str(item.fspath):
                item.add_marker(skip_db)
