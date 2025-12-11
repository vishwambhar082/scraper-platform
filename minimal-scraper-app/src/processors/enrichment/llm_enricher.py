"""
LLM Data Enrichment Pipeline.

Provides enrichment capabilities:
- Translation
- Metadata expansion
- OCR correction
- Duplicate detection
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from src.common.logging_utils import get_logger
from src.processors.llm.llm_client import LLMClient, get_llm_client_from_config

log = get_logger("llm-enricher")


def translate_record(
    record: Dict[str, Any],
    target_language: str,
    fields: Optional[List[str]] = None,
    llm_client: Optional[LLMClient] = None,
    source_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Translate text fields in a record to target language.
    
    Args:
        record: Record to translate
        target_language: Target language code (e.g., "en", "es", "fr")
        fields: Optional list of field names to translate (defaults to text fields)
        llm_client: Optional LLM client
        source_config: Optional source config for LLM client
    
    Returns:
        Record with translated fields
    """
    if llm_client is None:
        if source_config:
            llm_client = get_llm_client_from_config(source_config.get("llm", {}))
        else:
            raise ValueError("Either llm_client or source_config must be provided")
    
    if llm_client is None:
        log.warning("LLM client not available, skipping translation")
        return record
    
    # Default fields to translate
    if fields is None:
        fields = ["name", "description", "presentation", "company"]
    
    translated = record.copy()
    
    for field in fields:
        if field in record and record[field]:
            try:
                text = str(record[field])
                prompt = f"Translate the following text to {target_language}. Return only the translation, no explanation:\n\n{text}"
                result = llm_client.complete(prompt)
                translated[field] = result.strip()
            except Exception as exc:
                log.warning(f"Translation failed for field {field}", extra={"error": str(exc)})
    
    return translated


def expand_metadata(
    record: Dict[str, Any],
    llm_client: Optional[LLMClient] = None,
    source_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Expand record metadata using LLM.
    
    Adds inferred fields like:
    - category
    - tags
    - description_summary
    - related_products
    
    Args:
        record: Record to enrich
        llm_client: Optional LLM client
        source_config: Optional source config
    
    Returns:
        Record with expanded metadata
    """
    if llm_client is None:
        if source_config:
            llm_client = get_llm_client_from_config(source_config.get("llm", {}))
        else:
            return record
    
    if llm_client is None:
        return record
    
    try:
        # Build context from record
        context = "\n".join(f"{k}: {v}" for k, v in record.items() if v)
        
        prompt = f"""Analyze this product record and extract additional metadata:

{context}

Return JSON with:
- category: Product category
- tags: List of relevant tags
- description_summary: Brief summary
- inferred_fields: Any other useful inferred fields"""
        
        result = llm_client.extract_json(prompt)
        
        if isinstance(result, dict):
            # Merge inferred fields
            expanded = record.copy()
            for key, value in result.items():
                if key not in expanded or not expanded[key]:
                    expanded[key] = value
            
            return expanded
    
    except Exception as exc:
        log.warning("Metadata expansion failed", extra={"error": str(exc)})
    
    return record


def correct_ocr_errors(
    text: str,
    llm_client: Optional[LLMClient] = None,
    source_config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Correct OCR errors in text using LLM.
    
    Args:
        text: Text with potential OCR errors
        llm_client: Optional LLM client
        source_config: Optional source config
    
    Returns:
        Corrected text
    """
    if llm_client is None:
        if source_config:
            llm_client = get_llm_client_from_config(source_config.get("llm", {}))
        else:
            return text
    
    if llm_client is None:
        return text
    
    try:
        prompt = f"""Correct any OCR errors in this text. Return only the corrected text:

{text}"""
        
        result = llm_client.complete(prompt)
        return result.strip()
    
    except Exception as exc:
        log.warning("OCR correction failed", extra={"error": str(exc)})
        return text


def detect_duplicates(
    records: Iterable[Dict[str, Any]],
    llm_client: Optional[LLMClient] = None,
    source_config: Optional[Dict[str, Any]] = None,
) -> List[List[str]]:
    """
    Detect duplicate records using LLM.
    
    Args:
        records: Iterable of records to check
        llm_client: Optional LLM client
        source_config: Optional source config
    
    Returns:
        List of duplicate groups (each group is a list of record IDs/indices)
    """
    records_list = list(records)
    
    if len(records_list) < 2:
        return []
    
    if llm_client is None:
        if source_config:
            llm_client = get_llm_client_from_config(source_config.get("llm", {}))
        else:
            return []
    
    if llm_client is None:
        return []
    
    try:
        # Build comparison data
        records_json = json.dumps([{**r, "_index": i} for i, r in enumerate(records_list)], indent=2)
        
        prompt = f"""Analyze these records and identify duplicates. Duplicates are records that represent the same product.

{records_json}

Return JSON with:
- duplicate_groups: List of groups, each group is a list of indices of duplicate records"""
        
        result = llm_client.extract_json(prompt)
        
        if isinstance(result, dict):
            groups = result.get("duplicate_groups", [])
            return [group for group in groups if isinstance(group, list) and len(group) > 1]
    
    except Exception as exc:
        log.warning("Duplicate detection failed", extra={"error": str(exc)})
    
    return []

