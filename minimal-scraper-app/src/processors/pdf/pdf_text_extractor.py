"""
PDF text extractor using classic libraries (PyMuPDF, pdfplumber, etc.).

Extracts raw text and basic table structures from PDFs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.common.logging_utils import get_logger

log = get_logger("pdf-text-extractor")


def extract_pdf_text_classic(pdf_path: str | Path) -> Dict[str, Any]:
    """
    Extract text and basic tables from PDF using classic libraries.

    Tries PyMuPDF first, falls back to pdfplumber if available.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict with:
            - pages: List of page text
            - raw_tables: List of detected tables (if any)
            - page_count: Number of pages
            - extraction_method: Library used
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Try PyMuPDF first (faster)
    try:
        import fitz  # PyMuPDF  # type: ignore[import]

        doc = fitz.open(str(pdf_path))
        pages: List[str] = []
        raw_tables: List[Dict[str, Any]] = []

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            pages.append(text)

            # Try to detect tables (basic approach)
            # PyMuPDF can extract tables with newer versions
            try:
                tables = page.find_tables()
                for table in tables:
                    raw_tables.append({
                        "page": page_num,
                        "rows": table.extract(),
                    })
            except Exception:
                pass  # Table extraction not available or failed

        doc.close()

        return {
            "pages": pages,
            "raw_tables": raw_tables,
            "page_count": len(pages),
            "extraction_method": "pymupdf",
        }

    except ImportError:
        pass  # Try pdfplumber

    # Fallback to pdfplumber
    try:
        import pdfplumber  # type: ignore[import]

        pages: List[str] = []
        raw_tables: List[Dict[str, Any]] = []

        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append(text)

                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    raw_tables.append({
                        "page": page_num,
                        "rows": table,
                    })

        return {
            "pages": pages,
            "raw_tables": raw_tables,
            "page_count": len(pages),
            "extraction_method": "pdfplumber",
        }

    except ImportError:
        raise RuntimeError(
            "No PDF extraction library available. Install one of: "
            "pip install pymupdf OR pip install pdfplumber"
        )


def chunk_pdf_text(
    pages: List[str],
    chunk_size_chars: int = 6000,
    overlap_chars: int = 500,
) -> List[Dict[str, Any]]:
    """
    Chunk PDF text into smaller pieces for LLM processing.

    Args:
        pages: List of page text
        chunk_size_chars: Maximum characters per chunk
        overlap_chars: Characters to overlap between chunks

    Returns:
        List of chunks with metadata
    """
    chunks: List[Dict[str, Any]] = []
    current_chunk = ""
    current_page_start = 1

    for page_num, page_text in enumerate(pages, start=1):
        if len(current_chunk) + len(page_text) <= chunk_size_chars:
            # Add entire page to current chunk
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += page_text
        else:
            # Current chunk is full, save it
            if current_chunk:
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "page_start": current_page_start,
                    "page_end": page_num - 1,
                    "text": current_chunk,
                    "char_count": len(current_chunk),
                })

            # Start new chunk with overlap
            if overlap_chars > 0 and current_chunk:
                overlap_text = current_chunk[-overlap_chars:]
                current_chunk = overlap_text + "\n\n" + page_text
                current_page_start = page_num
            else:
                current_chunk = page_text
                current_page_start = page_num

            # If single page is too large, split it
            while len(current_chunk) > chunk_size_chars:
                split_point = chunk_size_chars - overlap_chars
                chunk_text = current_chunk[:split_point]
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "page_start": current_page_start,
                    "page_end": current_page_start,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                })
                current_chunk = current_chunk[split_point:]
                current_page_start = page_num

    # Add final chunk
    if current_chunk:
        chunks.append({
            "chunk_id": len(chunks) + 1,
            "page_start": current_page_start,
            "page_end": len(pages),
            "text": current_chunk,
            "char_count": len(current_chunk),
        })

    return chunks


def process_pdf_extraction(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    """
    Process records with PDF paths and extract text.

    Expects records with 'pdf_path' or 'pdf_id'.
    Adds 'pdf_text', 'pdf_pages', 'pdf_chunks' fields.

    Args:
        records: Iterable of records with PDF info

    Yields:
        Records with extracted text
    """
    for record in records:
        pdf_path = record.get("pdf_path")
        if not pdf_path:
            yield record
            continue

        try:
            extracted = extract_pdf_text_classic(pdf_path)
            record["pdf_text"] = "\n\n".join(extracted["pages"])
            record["pdf_pages"] = extracted["pages"]
            record["pdf_raw_tables"] = extracted["raw_tables"]
            record["pdf_page_count"] = extracted["page_count"]
            record["pdf_extraction_method"] = extracted["extraction_method"]
            yield record
        except Exception as exc:
            log.error(
                "Failed to extract PDF text",
                extra={"pdf_path": pdf_path, "error": str(exc)},
            )
            yield record

