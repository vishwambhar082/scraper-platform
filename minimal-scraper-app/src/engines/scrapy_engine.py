from __future__ import annotations

from typing import Any, Dict, Type

from src.common.logging_utils import get_logger

log = get_logger("scrapy-engine")

try:
    from scrapy.crawler import CrawlerProcess  # type: ignore[import]
    from scrapy.settings import Settings  # type: ignore[import]
except Exception:  # pragma: no cover
    CrawlerProcess = None  # type: ignore[assignment]
    Settings = None  # type: ignore[assignment]


def run_spider(spider_cls: Type[Any], settings_dict: Dict[str, Any] | None = None) -> None:
    """
    Run a Scrapy spider class using CrawlerProcess.

    This is a generic engine adapter; pipeline code is responsible for
    providing a spider_cls that yields items to the platform.

    Raises RuntimeError if Scrapy is not installed.
    """
    if CrawlerProcess is None or Settings is None:
        raise RuntimeError("Scrapy is not installed; scrapy engine unavailable")

    settings = Settings()
    if settings_dict:
        for k, v in settings_dict.items():
            settings.set(k, v)

    process = CrawlerProcess(settings)
    process.crawl(spider_cls)
    log.info("Starting Scrapy process for %s", getattr(spider_cls, "name", str(spider_cls)))
    process.start()
