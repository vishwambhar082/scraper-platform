"""
PDF fetcher processor.

Downloads PDFs from URLs and stores them for later processing.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.parse import urlparse

import requests
from src.common.logging_utils import get_logger
from src.common.paths import OUTPUT_DIR

log = get_logger("pdf-fetcher")

PDF_STORAGE_DIR = OUTPUT_DIR / "pdfs"


def fetch_and_store_pdf(pdf_url: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Fetch PDF from URL and store locally.

    Args:
        pdf_url: URL of PDF to fetch
        metadata: Optional metadata to attach

    Returns:
        Dict with:
            - pdf_id: Unique identifier for stored PDF
            - pdf_path: Local file path
            - pdf_url: Original URL
            - size_bytes: File size
            - metadata: Attached metadata
    """
    PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # Generate PDF ID from URL hash
    pdf_id = hashlib.sha256(pdf_url.encode()).hexdigest()[:16]
    pdf_id = f"PDF-{pdf_id}"

    # Determine file extension
    parsed = urlparse(pdf_url)
    ext = Path(parsed.path).suffix or ".pdf"
    if not ext.startswith("."):
        ext = f".{ext}"

    pdf_path = PDF_STORAGE_DIR / f"{pdf_id}{ext}"

    # Skip if already exists
    if pdf_path.exists():
        log.debug("PDF already cached", extra={"pdf_id": pdf_id, "url": pdf_url})
        return {
            "pdf_id": pdf_id,
            "pdf_path": str(pdf_path),
            "pdf_url": pdf_url,
            "size_bytes": pdf_path.stat().st_size,
            "metadata": metadata or {},
        }

    # Fetch PDF
    try:
        resp = requests.get(pdf_url, timeout=30, stream=True)
        resp.raise_for_status()

        # Verify content type
        content_type = resp.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
            log.warning(
                "URL may not be a PDF",
                extra={"url": pdf_url, "content_type": content_type},
            )

        # Save to disk
        with pdf_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size_bytes = pdf_path.stat().st_size
        log.info(
            "PDF fetched and stored",
            extra={"pdf_id": pdf_id, "url": pdf_url, "size_bytes": size_bytes},
        )

        return {
            "pdf_id": pdf_id,
            "pdf_path": str(pdf_path),
            "pdf_url": pdf_url,
            "size_bytes": size_bytes,
            "metadata": metadata or {},
        }

    except Exception as exc:
        log.error("Failed to fetch PDF", extra={"url": pdf_url, "error": str(exc)})
        raise


def process_pdf_urls(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    """
    Process records that contain PDF URLs.

    Expects records with 'pdf_url' field.
    Adds 'pdf_id' and 'pdf_path' fields.

    Args:
        records: Iterable of records with 'pdf_url'

    Yields:
        Records with added PDF metadata
    """
    for record in records:
        pdf_url = record.get("pdf_url")
        if not pdf_url:
            yield record
            continue

        try:
            pdf_info = fetch_and_store_pdf(pdf_url, metadata=record.get("metadata"))
            record["pdf_id"] = pdf_info["pdf_id"]
            record["pdf_path"] = pdf_info["pdf_path"]
            record["pdf_size_bytes"] = pdf_info["size_bytes"]
            yield record
        except Exception as exc:
            log.error(
                "Failed to process PDF URL",
                extra={"pdf_url": pdf_url, "error": str(exc)},
            )
            # Continue without PDF data
            yield record

