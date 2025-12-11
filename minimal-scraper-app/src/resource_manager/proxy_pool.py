# src/resource_manager/proxy_pool.py

"""Proxy pool with per-source settings and metrics."""

import os
import random
import time
from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Mapping, Optional, Sequence

import yaml

from src.common.logging_utils import get_logger, safe_log
from src.common.paths import CONFIG_DIR
from src.integrations.scraperapi import ScraperAPIClient, maybe_create_scraperapi_client
from src.observability import metrics
from src.resource_manager.settings import get_proxy_settings

log = get_logger("proxy-pool")


@dataclass
class ProxyStats:
    proxy: str
    success_count: int = 0
    failure_count: int = 0
    banned: bool = False
    banned_at: float = 0.0
    failure_history: Deque[float] = field(default_factory=deque)

    @property
    def score(self) -> float:
        # Simple heuristic: more successes, fewer failures; banned = terrible.
        if self.banned:
            return -1.0
        return self.success_count - 2 * self.failure_count


def _proxies_config_path() -> Path:
    return CONFIG_DIR / "proxies.yaml"


@lru_cache(maxsize=1)
def _load_proxies_blueprint(path: Optional[Path] = None) -> Dict[str, object]:
    """
    Load config/proxies.yaml once so every worker shares the same defaults.
    """

    cfg_path = path or _proxies_config_path()
    if not cfg_path.exists():
        return {}

    try:
        with cfg_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError("Proxy blueprint must be a mapping")
        return data
    except Exception as exc:  # noqa: BLE001
        safe_log(
            log,
            "warning",
            "Failed to load proxy blueprint",
            {"path": str(cfg_path), "error": str(exc)},
        )
    return {}


class ProxyPool:
    """Per-instance proxy pool to avoid module-level global state."""

    def __init__(
        self,
        settings: Optional[Mapping[str, object]] = None,
        *,
        blueprint_path: Optional[Path] = None,
    ):
        self._settings = settings or {}
        self._pools: Dict[str, Dict[str, ProxyStats]] = {}
        self._blueprint = _load_proxies_blueprint(blueprint_path)
        self._scraperapi_clients: Dict[str, ScraperAPIClient] = {}

    def _load_pool_for_source(self, source: str) -> Dict[str, ProxyStats]:
        """
        Load proxies for a source from env or injected settings.

        Settings override precedence:
        1. settings["proxies"][source] if provided as an iterable.
        2. settings[source]["proxies"] if provided as an iterable.
        3. Environment variable "{SOURCE}_PROXIES" as a comma-separated list.
        """

        proxies = self._get_proxies_from_settings(source)
        if proxies is None:
            proxies = self._get_proxies_from_blueprint(source)
        if proxies is None:
            env_key = f"{source.upper()}_PROXIES"
            raw = os.getenv(env_key, "").strip()
            proxies = [p.strip() for p in raw.split(",") if p.strip()]
            if not proxies:
                safe_log(
                    log,
                    "info",
                    f"No proxies configured via {env_key} for {source}; pool will be empty.",
                    {"env_key": env_key, "source": source},
                )
                return {}

            safe_log(
                log,
                "info",
                f"Loaded {len(proxies)} proxies for {source} from {env_key}",
                {"count": len(proxies), "source": source, "env_key": env_key},
            )
        else:
            safe_log(
                log,
                "info",
                "Loaded proxies for %s from injected settings",
                {"count": len(proxies), "source": source},
            )

        return {proxy: ProxyStats(proxy=proxy) for proxy in proxies}

    def _get_proxies_from_settings(self, source: str) -> Optional[List[str]]:
        if not isinstance(self._settings, Mapping):
            return None

        proxy_cfg = self._settings.get("proxies")
        if isinstance(proxy_cfg, Mapping):
            value = proxy_cfg.get(source)
            proxies = self._coerce_proxy_list(value)
            if proxies is not None:
                return proxies

        source_cfg = self._settings.get(source)
        if isinstance(source_cfg, Mapping):
            proxies = self._coerce_proxy_list(source_cfg.get("proxies"))
            if proxies is not None:
                return proxies

        return None

    def _get_proxies_from_blueprint(self, source: str) -> Optional[List[str]]:
        if not self._blueprint:
            return None

        per_source = (self._blueprint.get("per_source_overrides") or {}).get(source)
        defaults = self._blueprint.get("default_pool")

        merged: List[str] = []
        for cfg in filter(None, (per_source, defaults)):
            merged.extend(self._materialize_providers(cfg, source))

        return merged or None

    def _materialize_providers(self, cfg: Mapping[str, object], source: str) -> List[str]:
        providers: Sequence[Mapping[str, object]] = cfg.get("providers") or []  # type: ignore[assignment]
        if not providers:
            fallback = self._coerce_proxy_list(cfg.get("proxies"))
            return fallback or []

        materialized: List[str] = []
        for provider_cfg in providers:
            provider_type = (provider_cfg.get("type") or "static").lower()
            if provider_type == "static":
                static_values = self._coerce_proxy_list(provider_cfg.get("proxies"))
                if static_values:
                    materialized.extend(static_values)
            elif provider_type == "scraperapi":
                materialized.extend(self._materialize_scraperapi(provider_cfg, source))
            else:
                safe_log(
                    log,
                    "warning",
                    "Unknown proxy provider type",
                    {"type": provider_type, "source": source},
                )
        return materialized

    def _materialize_scraperapi(self, cfg: Mapping[str, object], source: str) -> List[str]:
        provider_name = cfg.get("name") or f"scraperapi-{source}"
        client = self._scraperapi_clients.get(provider_name)
        if client is None:
            client = maybe_create_scraperapi_client(cfg)
            if client is None:
                return []
            self._scraperapi_clients[provider_name] = client

        sticky_sessions = bool(cfg.get("sticky_sessions", True))
        session_pool_size = int(cfg.get("session_pool_size") or (5 if sticky_sessions else 1))
        session_prefix = cfg.get("session_prefix") or source
        country = cfg.get("country")
        premium = cfg.get("premium")

        proxies: List[str] = []
        if sticky_sessions and session_pool_size > 1:
            for idx in range(session_pool_size):
                session_id = f"{session_prefix}-{idx}"
                proxies.append(
                    client.build_proxy_string(
                        session_id=session_id,
                        country=country,
                        premium=premium,
                    )
                )
        else:
            proxies.append(
                client.build_proxy_string(
                    session_id=session_prefix if sticky_sessions else None,
                    country=country,
                    premium=premium,
                )
            )

        safe_log(
            log,
            "info",
            "Loaded ScraperAPI proxies",
            {"provider": provider_name, "source": source, "count": len(proxies)},
        )
        return proxies

    @staticmethod
    def _coerce_proxy_list(value: object) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            return [p.strip() for p in value.split(",") if p.strip()]
        if isinstance(value, Iterable):
            return [str(p).strip() for p in value if str(p).strip()]
        return None

    def _get_pool(self, source: str) -> Dict[str, ProxyStats]:
        if source not in self._pools:
            self._pools[source] = self._load_pool_for_source(source)
        return self._pools[source]

    def choose_proxy(self, source: str) -> Optional[str]:
        """
        Choose a proxy for the given source using a simple scoring scheme.
        Returns None if no proxies configured.
        """

        pool = self._get_pool(source)
        if not pool:
            return None

        proxy_settings = get_proxy_settings(source)
        ban_window_seconds = max(proxy_settings.get("ban_window_minutes", 30), 0) * 60

        now = time.time()
        for p in pool.values():
            if p.banned and p.banned_at and (now - p.banned_at) > ban_window_seconds:
                p.banned = False
                p.banned_at = 0.0

        active: List[ProxyStats] = [p for p in pool.values() if not p.banned] or list(pool.values())
        if not active:
            return None

        max_score = max(p.score for p in active)
        if max_score <= 0:
            chosen = random.choice(active)
            safe_log(
                log,
                "info",
                "Chose proxy",
                {"proxy": chosen.proxy, "source": source, "selection": "uniform"},
            )
            return chosen.proxy

        weights = [max(p.score, 0.0) for p in active]
        chosen = random.choices(active, weights=weights, k=1)[0]
        safe_log(
            log,
            "info",
            "Chose proxy",
            {"proxy": chosen.proxy, "source": source, "selection": "weighted"},
        )
        return chosen.proxy

    def mark_success(self, source: str, proxy: str) -> None:
        pool = self._get_pool(source)
        if proxy not in pool:
            return
        pool[proxy].success_count += 1
        ps = pool[proxy]
        safe_log(
            log,
            "debug",
            "Proxy success",
            {
                "proxy": proxy,
                "source": source,
                "success_count": ps.success_count,
                "failure_count": ps.failure_count,
                "banned": ps.banned,
            },
        )

    def mark_failure(self, source: str, proxy: str, ban: bool = False) -> None:
        pool = self._get_pool(source)
        if proxy not in pool:
            return
        proxy_settings = get_proxy_settings(source)
        max_errors_before_ban = proxy_settings.get("max_errors_before_ban", 3)
        ban_window_seconds = max(proxy_settings.get("ban_window_minutes", 30), 0) * 60
        now = time.time()

        ps = pool[proxy]
        ps.failure_count += 1
        ps.failure_history.append(now)
        while ps.failure_history and (now - ps.failure_history[0]) > ban_window_seconds:
            ps.failure_history.popleft()

        should_ban = ban or (
            max_errors_before_ban
            and max_errors_before_ban > 0
            and len(ps.failure_history) >= max_errors_before_ban
        )

        if should_ban:
            ps.banned = True
            ps.banned_at = now
            metrics.incr("proxy_ban_count", source=source, proxy_id=proxy)
            safe_log(
                log,
                "warning",
                "Proxy marked banned",
                {
                    "proxy": proxy,
                    "source": source,
                    "failure_count": ps.failure_count,
                    "banned": ps.banned,
                },
            )
        else:
            safe_log(
                log,
                "debug",
                "Proxy failure",
                {
                    "proxy": proxy,
                    "source": source,
                    "failure_count": ps.failure_count,
                    "banned": ps.banned,
                },
            )


_DEFAULT_POOL = ProxyPool()


def get_default_proxy_pool() -> ProxyPool:
    return _DEFAULT_POOL


def choose_proxy(source: str) -> Optional[str]:
    return _DEFAULT_POOL.choose_proxy(source)


def mark_success(source: str, proxy: str) -> None:
    _DEFAULT_POOL.mark_success(source, proxy)


def mark_failure(source: str, proxy: str, ban: bool = False) -> None:
    _DEFAULT_POOL.mark_failure(source, proxy, ban)
