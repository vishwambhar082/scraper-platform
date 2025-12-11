"""
Wrapper around tools.add_scraper_advanced for programmatic use.
"""
from __future__ import annotations

from tools.add_scraper_advanced import main as wizard_main


def create_source(name: str, engine: str = "selenium") -> int:
    return wizard_main(["--name", name, "--engine", engine])

