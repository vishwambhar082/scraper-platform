"""
Groq Browser Automation Engine.

Provides a thin wrapper around Groq's compound models with the built-in
``browser_automation`` tool so scrapers can launch managed browsers without
touching Selenium code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from src.common.logging_utils import get_logger, sanitize_for_log, safe_log

log = get_logger("groq-browser")

try:  # pragma: no cover - optional dependency import
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None  # type: ignore[assignment]


DEFAULT_BROWSER_MODEL = "groq/compound-mini"
DEFAULT_ENABLED_TOOLS = ["browser_automation", "web_search"]


@dataclass
class BrowserAutomationResult:
    """Structured result returned by Groq browser automation."""

    content: str
    executed_tools: List[Dict[str, Any]]
    usage: Dict[str, Any]
    raw_response: Dict[str, Any]


class GroqBrowserAutomationClient:
    """
    High-level helper that hides the Groq client boilerplate.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = DEFAULT_BROWSER_MODEL,
        enabled_tools: Optional[Sequence[str]] = None,
        groq_client: Optional[Groq] = None,
        base_url: Optional[str] = None,
    ):
        if groq_client is None and Groq is None:
            raise RuntimeError(
                "groq package is not installed. Install it with `pip install groq`."
            )

        resolved_key = api_key or os.getenv("GROQ_API_KEY", "")
        if not resolved_key and groq_client is None:
            raise ValueError("Missing GROQ_API_KEY. Set env or pass api_key explicitly.")

        self.model = model
        self.enabled_tools = list(enabled_tools or DEFAULT_ENABLED_TOOLS)
        self._client = groq_client or Groq(api_key=resolved_key, base_url=base_url)  # type: ignore[misc]

    def run_workflow(
        self,
        instructions: str,
        *,
        start_url: Optional[str] = None,
        max_browser_time: int = 120,
        capture_screenshots: bool = True,
        system_prompt: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> BrowserAutomationResult:
        """
        Execute a browser automation workflow powered by Groq's compound models.
        """

        compound: MutableMapping[str, Any] = {
            "tools": {
                "enabled_tools": self.enabled_tools,
            },
            "browser_automation": {
                "start_url": start_url,
                "max_duration_seconds": max_browser_time,
                "capture_screenshots": capture_screenshots,
            },
        }
        if metadata:
            compound["metadata"] = dict(metadata)

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": instructions})

        safe_log(
            log,
            "info",
            "Executing Groq browser workflow",
            extra=sanitize_for_log(
                {
                    "start_url": start_url,
                    "model": self.model,
                    "enabled_tools": self.enabled_tools,
                }
            ),
        )

        response = self._client.chat.completions.create(  # type: ignore[union-attr]
            model=self.model,
            messages=messages,
            compound_custom=compound,
        )

        choice = response.choices[0].message
        content = (choice.content or "").strip()
        executed_tools = _normalize_tool_events(choice.executed_tools or [])

        usage = getattr(response, "usage", {}) or {}
        safe_log(
            log,
            "info",
            "Groq browser workflow complete",
            extra=sanitize_for_log(
                {
                    "tokens_in": usage.get("prompt_tokens"),
                    "tokens_out": usage.get("completion_tokens"),
                    "tool_count": len(executed_tools),
                }
            ),
        )

        return BrowserAutomationResult(
            content=content,
            executed_tools=executed_tools,
            usage=dict(usage),
            raw_response=response.to_dict() if hasattr(response, "to_dict") else response,  # type: ignore[arg-type]
        )


def _normalize_tool_events(events: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for event in events:
        entry = {
            "name": event.get("name"),
            "status": event.get("status"),
            "started_at": event.get("started_at"),
            "completed_at": event.get("completed_at"),
            "output": event.get("output"),
        }
        normalized.append(entry)
    return normalized


__all__ = ["GroqBrowserAutomationClient", "BrowserAutomationResult"]

