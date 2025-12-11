"""HTTP fetch agent that wraps the existing HTTP engine."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from src.common.logging_utils import get_logger
from src.engines import build_rate_limiter_from_config, get_http_engine

from .base import AgentConfig, AgentContext, BaseAgent

log = get_logger("agents.http")


class HttpFetchAgent(BaseAgent):
    """Fetch a single URL and store response text in the context."""

    def __init__(self, *, config: Optional[AgentConfig] = None) -> None:
        super().__init__(config=config)

    def _resolve_url(self, context: AgentContext) -> str:
        url = context.get("url") or context.get_nested("request.url")
        if url:
            return str(url)

        source_cfg: Mapping[str, Any] = context.metadata.get("source_config", {})
        base_url = source_cfg.get("base_url") or source_cfg.get("url")
        if not base_url:
            raise ValueError("HttpFetchAgent requires 'url' in context or source_config.base_url")
        return str(base_url)

    def run(self, context: AgentContext) -> AgentContext:
        send_request, HttpRequestConfig = get_http_engine()

        url = self._resolve_url(context)
        runtime_settings: Mapping[str, Any] = context.metadata.get("settings", {})
        rate_limiter = build_rate_limiter_from_config(runtime_settings) if runtime_settings else None

        request_config = HttpRequestConfig(
            url=url,
            timeout=self.config.timeout,
            max_retries=self.config.retries,
            backoff_seconds=self.config.backoff_seconds,
            proxy=context.metadata.get("proxy"),
            headers=context.metadata.get("headers"),
        )

        log.info("Fetching %s", url)
        result = send_request(request_config, rate_limiter=rate_limiter)

        context["raw_html"] = result.text
        context.metadata.setdefault("response", {})
        context.metadata["response"].update(
            {
                "status_code": result.status_code,
                "url": result.url,
                "headers": result.headers,
                "elapsed_seconds": result.elapsed_seconds,
            }
        )
        return context


__all__ = ["HttpFetchAgent"]
