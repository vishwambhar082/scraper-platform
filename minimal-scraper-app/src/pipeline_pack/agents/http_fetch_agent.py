from __future__ import annotations

from typing import Any, Dict, Optional
import logging

from .base import BaseAgent, AgentContext
from src.pipeline_pack.engines.engine_factory import build_engine

logger = logging.getLogger(__name__)


class HttpFetchAgent(BaseAgent):
    name = "http_fetch"

    def execute(self, ctx: AgentContext) -> AgentContext:
        url: str = ctx.request.get("url") or self.config.get("url")
        if not url:
            ctx.add_error("HttpFetchAgent: no URL provided")
            return ctx

        engine_type = self.config.get("engine_type", "http")
        engine_cfg: Dict[str, Any] = self.config.get("engine_config", {})
        engine = build_engine(engine_type, **engine_cfg)

        method = ctx.request.get("method", "GET")
        headers = ctx.request.get("headers")
        params = ctx.request.get("params")
        data = ctx.request.get("data")
        json_body = ctx.request.get("json")
        proxies = ctx.request.get("proxies")

        resp = engine.fetch(
            url=url,
            method=method,
            headers=headers,
            params=params,
            data=data,
            json_body=json_body,
            proxies=proxies,
        )

        ctx.response = {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "url": resp.url,
        }
        ctx.html = resp.text
        try:
            ctx.json_data = resp.json()
        except Exception:
            ctx.json_data = None
        return ctx


__all__ = ["HttpFetchAgent"]
