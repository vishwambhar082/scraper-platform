"""
LLM-based patch generator for DeepAgent auto-repair.

Uses LLM to generate code patches when scrapers fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.agents.llm_selector_engine import repair_selectors_with_llm
from src.common.logging_utils import get_logger
from src.processors.llm.llm_client import LLMClient, get_llm_client_from_config

log = get_logger("llm-patch-generator")


@dataclass
class PatchProposal:
    """Represents a code patch proposal."""

    file_path: str
    old_code: str
    new_code: str
    description: str
    confidence: float
    affected_lines: List[int]


def generate_selector_patch_with_llm(
    html_old: str,
    html_new: str,
    old_selectors: Dict[str, str],
    error_message: str,
    llm_client: LLMClient,
) -> Dict[str, str]:
    """
    Generate updated selectors using LLM when selectors break.

    Args:
        html_old: HTML when selectors worked
        html_new: HTML where selectors broke
        old_selectors: Broken selectors
        error_message: Error message from failed extraction
        llm_client: LLM client instance

    Returns:
        Updated selectors dict
    """
    fields = list(old_selectors.keys())
    return repair_selectors_with_llm(html_old, html_new, old_selectors, fields, llm_client)


def generate_code_patch_with_llm(
    file_path: str,
    current_code: str,
    error_message: str,
    context: Dict[str, Any],
    llm_client: LLMClient,
) -> Optional[PatchProposal]:
    """
    Generate a code patch using LLM to fix a scraper failure.

    Args:
        file_path: Path to file that needs patching
        current_code: Current code content
        error_message: Error that occurred
        context: Additional context (HTML, selectors, etc.)
        llm_client: LLM client instance

    Returns:
        PatchProposal or None if patch generation failed
    """
    system_prompt = """You are a Python code repair expert. Analyze broken scraper code and generate
a minimal, focused patch to fix the issue. Return only the patched code section, not the entire file.

Return JSON with:
{
  "old_code": "code to replace",
  "new_code": "replacement code",
  "description": "what this patch fixes",
  "confidence": 0.0-1.0,
  "affected_lines": [start_line, end_line]
}"""

    context_str = "\n".join(f"{k}: {str(v)[:500]}" for k, v in context.items())

    prompt = f"""File: {file_path}

Current code:
```python
{current_code[:3000]}
```

Error:
{error_message}

Context:
{context_str}

Generate a minimal patch to fix this error. Return JSON with old_code, new_code, description, confidence, and affected_lines."""

    try:
        result = llm_client.extract_json(prompt, system_prompt=system_prompt)
        if isinstance(result, dict):
            return PatchProposal(
                file_path=file_path,
                old_code=result.get("old_code", ""),
                new_code=result.get("new_code", ""),
                description=result.get("description", "LLM-generated patch"),
                confidence=float(result.get("confidence", 0.5)),
                affected_lines=result.get("affected_lines", []),
            )
        else:
            log.warning("LLM returned invalid patch format")
            return None
    except Exception as exc:
        log.error("Failed to generate code patch with LLM", extra={"error": str(exc)})
        return None


def generate_repair_patches(
    source: str,
    source_config: Dict[str, Any],
    failure_context: Dict[str, Any],
) -> List[PatchProposal]:
    """
    Generate repair patches for a failed scraper run.

    Args:
        source: Source name
        source_config: Source config
        failure_context: Context about the failure:
            - error_message: str
            - html_old: str (optional)
            - html_new: str (optional)
            - old_selectors: Dict (optional)
            - file_path: str (optional)
            - current_code: str (optional)

    Returns:
        List of patch proposals
    """
    llm_config = source_config.get("llm", {})
    if not llm_config.get("enabled", False):
        log.info("LLM not enabled, skipping patch generation")
        return []

    llm_client = get_llm_client_from_config(source_config)
    if not llm_client:
        log.warning("LLM client not available")
        return []

    patches: List[PatchProposal] = []

    # Try selector repair first
    if "html_old" in failure_context and "html_new" in failure_context:
        old_selectors = failure_context.get("old_selectors", {})
        if old_selectors:
            try:
                new_selectors = generate_selector_patch_with_llm(
                    failure_context["html_old"],
                    failure_context["html_new"],
                    old_selectors,
                    failure_context.get("error_message", ""),
                    llm_client,
                )
                # Convert selector update to patch proposal
                if new_selectors:
                    patches.append(
                        PatchProposal(
                            file_path=f"src/scrapers/{source}/selectors.json",
                            old_code=str(old_selectors),
                            new_code=str(new_selectors),
                            description="Updated selectors to match new HTML structure",
                            confidence=0.7,
                            affected_lines=[],
                        )
                    )
            except Exception as exc:
                log.error("Selector patch generation failed", extra={"error": str(exc)})

    # Try code patch generation
    if "file_path" in failure_context and "current_code" in failure_context:
        try:
            patch = generate_code_patch_with_llm(
                failure_context["file_path"],
                failure_context["current_code"],
                failure_context.get("error_message", ""),
                failure_context,
                llm_client,
            )
            if patch:
                patches.append(patch)
        except Exception as exc:
            log.error("Code patch generation failed", extra={"error": str(exc)})

    return patches
