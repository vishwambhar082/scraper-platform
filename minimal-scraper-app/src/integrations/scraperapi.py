"""
ScraperAPI integration helpers.

This module centralizes how we build ScraperAPI request URLs and synthetic proxy
strings so the rest of the platform can treat ScraperAPI as a drop-in proxy
provider or HTTP adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping, Optional
from urllib.parse import urlencode
import os

from src.common.logging_utils import get_logger, safe_log

log = get_logger("scraperapi")


_DEFAULT_BASE_URL = "https://api.scraperapi.com"
_DEFAULT_PROXY_HOST = "proxy-server.scraperapi.com"
_DEFAULT_PROXY_PORT = 8001


@dataclass
class ScraperAPISettings:
    """
    Strongly typed settings for initializing a ScraperAPI client.
    """

    api_key: str
    base_url: str = _DEFAULT_BASE_URL
    proxy_hostname: str = _DEFAULT_PROXY_HOST
    proxy_port: int = _DEFAULT_PROXY_PORT
    default_params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, cfg: Mapping[str, Any]) -> "ScraperAPISettings":
        env_key = cfg.get("api_key_env") or "SCRAPERAPI_API_KEY"
        api_key = cfg.get("api_key") or os.getenv(env_key, "")
        if not api_key:
            raise ValueError("ScraperAPI api_key missing. Provide api_key or api_key_env.")

        params = dict(cfg.get("default_params") or {})
        return cls(
            api_key=api_key,
            base_url=cfg.get("base_url") or _DEFAULT_BASE_URL,
            proxy_hostname=cfg.get("proxy_hostname") or _DEFAULT_PROXY_HOST,
            proxy_port=int(cfg.get("proxy_port") or _DEFAULT_PROXY_PORT),
            default_params=params,
        )


class ScraperAPIClient:
    """
    Helper that knows how to build ScraperAPI request URLs or proxy strings.
    """

    def __init__(self, settings: ScraperAPISettings):
        self.settings = settings

    def build_request_url(
        self,
        target_url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """
        Return the fully qualified ScraperAPI URL that will fetch ``target_url``.
        """

        query: MutableMapping[str, Any] = dict(self.settings.default_params)
        if params:
            query.update({k: v for k, v in params.items() if v is not None})
        query["api_key"] = self.settings.api_key
        query["url"] = target_url
        encoded = urlencode(query, doseq=True)
        return f"{self.settings.base_url.rstrip('/')}/?{encoded}"

    def build_proxy_string(
        self,
        *,
        session_id: Optional[str] = None,
        country: Optional[str] = None,
        premium: Optional[bool] = None,
    ) -> str:
        """
        Return a proxy URL (http://user:pass@host:port) that leverages the
        ScraperAPI proxy gateway. Additional parameters are encoded via the
        username/password segment as documented by ScraperAPI.
        """

        params: Dict[str, Any] = dict(self.settings.default_params)
        if session_id:
            params["session_number"] = session_id
        if country:
            params["country_code"] = country
        if premium is not None:
            params["premium"] = "true" if premium else "false"

        if params:
            extra = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            username = f"scraperapi:{self.settings.api_key}:{extra}"
        else:
            username = f"scraperapi:{self.settings.api_key}"

        proxy = f"http://{username}@{self.settings.proxy_hostname}:{self.settings.proxy_port}"
        safe_log(log, "debug", "Constructed ScraperAPI proxy", {"proxy": proxy})
        return proxy


def maybe_create_scraperapi_client(cfg: Optional[Mapping[str, Any]]) -> Optional[ScraperAPIClient]:
    """
    Convenience helper that returns a ScraperAPI client if cfg enables it.
    """

    if not cfg:
        return None
    enabled = cfg.get("enabled", True)
    if not enabled:
        return None
    try:
        settings = ScraperAPISettings.from_mapping(cfg)
    except ValueError as exc:
        safe_log(log, "warning", "Skipping ScraperAPI provider", {"error": str(exc)})
        return None
    return ScraperAPIClient(settings)


__all__ = [
    "ScraperAPIClient",
    "ScraperAPISettings",
    "maybe_create_scraperapi_client",
]

