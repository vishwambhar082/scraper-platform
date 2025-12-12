"""
LLM Debugger / Inspection Tools.

Provides diagnostic capabilities:
- Analyze failures
- Suggest fixes
- Root cause analysis
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.common.logging_utils import get_logger
from src.processors.llm.llm_client import LLMClient, get_llm_client_from_config

log = get_logger("llm-debugger")


def analyze_failure(
    error_message: str,
    context: Optional[Dict[str, Any]] = None,
    llm_client: Optional[LLMClient] = None,
    source_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyze a failure and provide diagnostic information.

    Args:
        error_message: Error message or exception
        context: Optional context (logs, stack trace, run info)
        llm_client: Optional LLM client
        source_config: Optional source config

    Returns:
        Dict with:
            - root_cause: Identified root cause
            - severity: Error severity (low/medium/high/critical)
            - suggested_fixes: List of suggested fixes
            - related_issues: Related known issues
    """
    if llm_client is None:
        if source_config:
            llm_client = get_llm_client_from_config(source_config.get("llm", {}))
        else:
            return {
                "root_cause": "Unknown (LLM not available)",
                "severity": "medium",
                "suggested_fixes": [],
                "related_issues": [],
            }

    if llm_client is None:
        return {
            "root_cause": "Unknown (LLM not configured)",
            "severity": "medium",
            "suggested_fixes": [],
            "related_issues": [],
        }

    try:
        context_str = ""
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())

        prompt = f"""Analyze this scraper failure and provide diagnostics:

Error: {error_message}

Context:
{context_str if context_str else "No additional context"}

Return JSON with:
- root_cause: Brief description of the root cause
- severity: One of: low, medium, high, critical
- suggested_fixes: List of suggested fixes
- related_issues: List of related known issues or patterns"""

        result = llm_client.extract_json(prompt)

        if isinstance(result, dict):
            return {
                "root_cause": result.get("root_cause", "Unknown"),
                "severity": result.get("severity", "medium"),
                "suggested_fixes": result.get("suggested_fixes", []),
                "related_issues": result.get("related_issues", []),
            }

    except Exception as exc:
        log.error("Failure analysis failed", extra={"error": str(exc)})

    return {
        "root_cause": "Analysis failed",
        "severity": "medium",
        "suggested_fixes": [],
        "related_issues": [],
    }


def suggest_fixes(
    issue_description: str,
    current_config: Optional[Dict[str, Any]] = None,
    llm_client: Optional[LLMClient] = None,
    source_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Suggest fixes for an issue.

    Args:
        issue_description: Description of the issue
        current_config: Current configuration (selectors, config, etc.)
        llm_client: Optional LLM client
        source_config: Optional source config

    Returns:
        List of suggested fixes, each with:
            - description: What to change
            - confidence: Confidence level (0.0 to 1.0)
            - impact: Expected impact
    """
    if llm_client is None:
        if source_config:
            llm_client = get_llm_client_from_config(source_config.get("llm", {}))
        else:
            return []

    if llm_client is None:
        return []

    try:
        config_str = ""
        if current_config:
            config_str = f"\nCurrent config:\n{json.dumps(current_config, indent=2)}"

        prompt = f"""Suggest fixes for this scraper issue:

Issue: {issue_description}
{config_str}

Return JSON with:
- fixes: List of fixes, each with:
  - description: What to change
  - confidence: Confidence level (0.0 to 1.0)
  - impact: Expected impact description"""

        result = llm_client.extract_json(prompt)

        if isinstance(result, dict):
            fixes = result.get("fixes", [])
            return [
                {
                    "description": fix.get("description", ""),
                    "confidence": float(fix.get("confidence", 0.5)),
                    "impact": fix.get("impact", ""),
                }
                for fix in fixes
            ]

    except Exception as exc:
        log.error("Fix suggestion failed", extra={"error": str(exc)})

    return []


def root_cause_analysis(
    symptoms: List[str],
    logs: Optional[List[str]] = None,
    llm_client: Optional[LLMClient] = None,
    source_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Perform root cause analysis.

    Args:
        symptoms: List of observed symptoms
        logs: Optional log excerpts
        llm_client: Optional LLM client
        source_config: Optional source config

    Returns:
        Dict with:
            - root_cause: Identified root cause
            - contributing_factors: List of contributing factors
            - timeline: Suggested timeline of events
            - prevention: Suggestions for prevention
    """
    if llm_client is None:
        if source_config:
            llm_client = get_llm_client_from_config(source_config.get("llm", {}))
        else:
            return {
                "root_cause": "Unknown (LLM not available)",
                "contributing_factors": [],
                "timeline": [],
                "prevention": [],
            }

    if llm_client is None:
        return {
            "root_cause": "Unknown (LLM not configured)",
            "contributing_factors": [],
            "timeline": [],
            "prevention": [],
        }

    try:
        symptoms_str = "\n".join(f"- {s}" for s in symptoms)
        logs_str = ""
        if logs:
            logs_str = f"\nLogs:\n" + "\n".join(logs[:20])  # Limit log size

        prompt = f"""Perform root cause analysis for this scraper issue:

Symptoms:
{symptoms_str}
{logs_str}

Return JSON with:
- root_cause: Primary root cause
- contributing_factors: List of contributing factors
- timeline: Suggested timeline of events leading to the issue
- prevention: Suggestions for preventing this issue in the future"""

        result = llm_client.extract_json(prompt)

        if isinstance(result, dict):
            return {
                "root_cause": result.get("root_cause", "Unknown"),
                "contributing_factors": result.get("contributing_factors", []),
                "timeline": result.get("timeline", []),
                "prevention": result.get("prevention", []),
            }

    except Exception as exc:
        log.error("Root cause analysis failed", extra={"error": str(exc)})

    return {
        "root_cause": "Analysis failed",
        "contributing_factors": [],
        "timeline": [],
        "prevention": [],
    }
