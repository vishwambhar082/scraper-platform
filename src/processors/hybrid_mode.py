"""
Hybrid mode processor: try classic first, fallback to LLM.

Implements the hybrid strategy where classic parsing is attempted first,
and LLM is only used if classic fails or quality is below threshold.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from src.common.logging_utils import get_logger
from src.processors.pdf.pdf_text_extractor import extract_pdf_text_classic
from src.processors.pdf.pdf_table_llm import extract_table_with_llm
from src.processors.llm.llm_client import get_llm_client_from_config

log = get_logger("hybrid-mode")


def score_classic_extraction(extracted: Dict[str, Any]) -> float:
    """
    Score classic extraction quality.

    Args:
        extracted: Result from classic extraction

    Returns:
        Score from 0.0 to 1.0
    """
    score = 0.0

    # Check if we got tables
    raw_tables = extracted.get("raw_tables", [])
    if raw_tables:
        score += 0.5
        # Check table quality (row count, completeness)
        for table in raw_tables:
            rows = table.get("rows", [])
            if len(rows) > 5:  # Reasonable table size
                score += 0.2
            if rows and len(rows[0]) >= 3:  # Reasonable column count
                score += 0.2

    # Check if we got text
    pages = extracted.get("pages", [])
    if pages:
        total_text = sum(len(p) for p in pages)
        if total_text > 100:  # Non-empty
            score += 0.1

    return min(score, 1.0)


def process_pdf_hybrid(
    records: Iterable[Dict[str, Any]],
    source_config: Dict[str, Any],
    table_schema: Dict[str, List[str]],
    quality_threshold: float = 0.7,
) -> Iterable[Dict[str, Any]]:
    """
    Process PDFs in hybrid mode: classic first, LLM fallback.

    Args:
        records: Records with PDF paths
        source_config: Source config
        table_schema: Table schema for LLM extraction
        quality_threshold: Minimum quality score to accept classic extraction

    Yields:
        Records with extracted tables
    """
    llm_config = source_config.get("llm", {})
    llm_client = get_llm_client_from_config(source_config) if llm_config.get("enabled") else None

    for record in records:
        pdf_path = record.get("pdf_path")
        if not pdf_path:
            yield record
            continue

        try:
            # Step 1: Try classic extraction
            extracted = extract_pdf_text_classic(pdf_path)
            score = score_classic_extraction(extracted)

            record["pdf_pages"] = extracted["pages"]
            record["pdf_raw_tables"] = extracted["raw_tables"]
            record["pdf_extraction_method"] = extracted["extraction_method"]
            record["_classic_score"] = score

            # Step 2: Decide if we need LLM
            if score >= quality_threshold and extracted.get("raw_tables"):
                # Classic is good enough
                log.info(
                    "Using classic extraction (score >= threshold)",
                    extra={"pdf_id": record.get("pdf_id"), "score": score},
                )
                record["_extraction_mode"] = "classic"
            elif llm_client:
                # Fallback to LLM
                log.info(
                    "Classic extraction insufficient, using LLM",
                    extra={"pdf_id": record.get("pdf_id"), "score": score},
                )

                # Get table schema
                table_type = source_config.get("table_type", "default")
                columns = table_schema.get(table_type, table_schema.get("default", []))

                # Extract with LLM
                pdf_text = "\n\n".join(extracted["pages"])
                rows = extract_table_with_llm(pdf_text, columns, llm_client)

                record["extracted_tables"] = {
                    "table_type": table_type,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                }
                record["_extraction_mode"] = "llm"
            else:
                # No LLM available, use classic even if low quality
                record["_extraction_mode"] = "classic"
                log.warning(
                    "Classic extraction low quality but LLM not available",
                    extra={"pdf_id": record.get("pdf_id"), "score": score},
                )

        except Exception as exc:
            log.error(
                "Hybrid PDF processing failed",
                extra={"pdf_id": record.get("pdf_id"), "error": str(exc)},
            )

        yield record


def should_use_llm(
    source_config: Dict[str, Any],
    stage: str,
) -> bool:
    """
    Determine if LLM should be used for a given stage.

    Args:
        source_config: Source config
        stage: Stage name ('extract_engine', 'pdf_to_table', 'normalize', 'qc')

    Returns:
        True if LLM should be used
    """
    mode = source_config.get("mode", {})
    llm_config = source_config.get("llm", {})

    if not llm_config.get("enabled", False):
        return False

    if stage == "extract_engine":
        return mode.get("extract_engine") in ("llm", "hybrid")
    elif stage == "pdf_to_table":
        return mode.get("pdf_to_table") in ("llm", "hybrid")
    elif stage == "normalize":
        return llm_config.get("normalize_fields", []) != []
    elif stage == "qc":
        return llm_config.get("qc_enabled", False)
    else:
        return False

