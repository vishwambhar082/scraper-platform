"""Scraper plugins map to concrete scraper pipelines and steps."""

from src.scrapers.alfabeta.pipeline import run_alfabeta
from src.scrapers.template.pipeline import run_template

__all__ = ["run_alfabeta", "run_template"]
