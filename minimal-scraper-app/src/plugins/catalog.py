from __future__ import annotations

from src.plugins.registry import Plugin

BUILTIN_PLUGINS = [
    Plugin(
        name="scraper.alfabeta.pipeline",
        module="src.plugins.scrapers.alfabeta",
        entrypoint="run_alfabeta",
        type="scraper",
        description="Full AlfaBeta pipeline executable via DSL or plugin loader.",
    ),
    Plugin(
        name="scraper.template.pipeline",
        module="src.plugins.scrapers.template",
        entrypoint="run_template",
        type="scraper",
        description="Minimal sample pipeline for smoke testing the platform stack.",
    ),
    Plugin(
        name="engine.playwright.goto_with_retry",
        module="src.plugins.engines.playwright",
        entrypoint="goto_with_retry",
        type="engine",
        description="Navigate pages with retry/backoff and optional proxy failover.",
    ),
    Plugin(
        name="engine.selenium.open_with_session",
        module="src.plugins.engines.selenium",
        entrypoint="open_with_session",
        type="engine",
        description="Open a Selenium session with cookie restore and retry semantics.",
    ),
    Plugin(
        name="processor.pcid.build_index",
        module="src.plugins.processors.pcid",
        entrypoint="build_pcid_index",
        type="processor",
        description="Construct an exact-match PCID index from master records.",
    ),
    Plugin(
        name="processor.pcid.match_records",
        module="src.plugins.processors.pcid",
        entrypoint="match_records",
        type="processor",
        description="Match unified records to PCIDs via vector store and deterministic rules.",
    ),
    Plugin(
        name="processor.dedupe.records",
        module="src.plugins.processors.dedupe",
        entrypoint="dedupe_records",
        type="processor",
        description="Remove duplicate records using a configurable key tuple.",
    ),
]
