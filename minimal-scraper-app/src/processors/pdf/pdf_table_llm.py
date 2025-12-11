"""
LLM-based PDF table extractor.

Uses LLM to extract structured tables from PDF text chunks.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.common.logging_utils import get_logger
from src.processors.llm.llm_client import LLMClient, get_llm_client_from_config
from src.processors.pdf.pdf_text_extractor import chunk_pdf_text

log = get_logger("pdf-table-llm")


def extract_table_with_llm(
    text_chunk: str,
    columns: List[str],
    llm_client: LLMClient,
    system_prompt: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Extract table from text chunk using LLM.

    Args:
        text_chunk: Text to extract from
        columns: List of column names for the table
        llm_client: LLM client instance
        system_prompt: Optional custom system prompt

    Returns:
        List of row dicts
    """
    if not system_prompt:
        system_prompt = (
            "You are a data extraction specialist. Extract structured data from text "
            "and return it as a JSON array of objects."
        )

    columns_str = ", ".join(columns)
    prompt = f"""Extract a table from the following text with columns: {columns_str}

Text:
{text_chunk}

Return a JSON array where each object has these keys: {columns_str}
Only include rows where you can extract all required columns.
Return only valid JSON, no markdown, no explanation."""

    try:
        result = llm_client.extract_json(prompt, system_prompt=system_prompt)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            # Sometimes LLM returns single object
            return [result]
        else:
            log.warning("Unexpected LLM response format", extra={"result_type": type(result)})
            return []
    except Exception as exc:
        log.error("LLM table extraction failed", extra={"error": str(exc)})
        return []


def process_pdf_table_llm(
    records: Iterable[Dict[str, Any]],
    source_config: Dict[str, Any],
    table_schema: Dict[str, List[str]],
) -> Iterable[Dict[str, Any]]:
    """
    Process PDF records and extract tables using LLM.

    Args:
        records: Records with 'pdf_pages' or 'pdf_text'
        source_config: Source config with LLM settings
        table_schema: Dict mapping table types to column lists
            e.g., {"price_list": ["drug_name", "strength", "pack", "mrp", "manufacturer"]}

    Yields:
        Records with 'extracted_tables' field
    """
    llm_config = source_config.get("llm", {})
    pdf_config = llm_config.get("pdf", {})
    
    chunk_size = pdf_config.get("chunk_size_chars", 6000)
    overlap = pdf_config.get("overlap_chars", 500)

    # Get LLM client
    llm_client = get_llm_client_from_config(source_config)
    if not llm_client:
        log.warning("LLM not enabled for this source, skipping LLM table extraction")
        for record in records:
            yield record
        return

    # Determine table type (default to first schema or 'default')
    table_type = source_config.get("table_type", "default")
    if table_type not in table_schema:
        table_type = list(table_schema.keys())[0] if table_schema else "default"
    
    columns = table_schema.get(table_type, table_schema.get("default", []))

    for record in records:
        pdf_pages = record.get("pdf_pages")
        pdf_text = record.get("pdf_text")
        
        if not pdf_pages and not pdf_text:
            yield record
            continue

        try:
            # Chunk the text
            if pdf_pages:
                chunks = chunk_pdf_text(pdf_pages, chunk_size, overlap)
            else:
                # Single text, split into chunks
                chunks = chunk_pdf_text([pdf_text], chunk_size, overlap)

            # Extract tables from each chunk
            all_rows: List[Dict[str, Any]] = []
            for chunk in chunks:
                rows = extract_table_with_llm(
                    chunk["text"],
                    columns,
                    llm_client,
                )
                # Add chunk metadata to rows
                for row in rows:
                    row["_chunk_id"] = chunk["chunk_id"]
                    row["_page_range"] = f"{chunk['page_start']}-{chunk['page_end']}"
                all_rows.extend(rows)

            # Deduplicate rows (simple key-based)
            if columns:
                key_cols = columns[:2] if len(columns) >= 2 else columns
                seen_keys = set()
                unique_rows = []
                for row in all_rows:
                    key = tuple(str(row.get(col, "")).lower() for col in key_cols)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        unique_rows.append(row)
                all_rows = unique_rows

            record["extracted_tables"] = {
                "table_type": table_type,
                "columns": columns,
                "rows": all_rows,
                "row_count": len(all_rows),
            }

            log.info(
                "Extracted table with LLM",
                extra={
                    "pdf_id": record.get("pdf_id"),
                    "row_count": len(all_rows),
                    "chunks_processed": len(chunks),
                },
            )

        except Exception as exc:
            log.error(
                "Failed to extract table with LLM",
                extra={"pdf_id": record.get("pdf_id"), "error": str(exc)},
            )

        yield record

