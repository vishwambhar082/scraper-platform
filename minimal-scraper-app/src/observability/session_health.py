# src/observability/session_health.py

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.common.paths import COOKIES_DIR, SESSION_LOGS_DIR
from src.common.logging_utils import get_logger

log = get_logger("session-health")

SESSION_EVENTS_PATH = SESSION_LOGS_DIR / "session_events.jsonl"


@dataclass
class SessionHealth:
    source: str
    account_id: str
    proxy_id: str
    has_cookie_file: bool
    last_seen_at: Optional[str]
    last_event_type: Optional[str]


def _load_session_events() -> List[Dict]:
    if not SESSION_EVENTS_PATH.exists():
        return []
    events: List[Dict] = []
    with SESSION_EVENTS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                log.warning("Skipping bad session event line: %r", line[:200])
    return events


def get_session_health(source: Optional[str] = None) -> List[SessionHealth]:
    events = _load_session_events()
    by_key: Dict[tuple, Dict] = {}

    for ev in events:
        if source and ev.get("source") != source:
            continue
        key = (ev.get("source"), ev.get("account_id"), ev.get("proxy_id"))
        prev = by_key.get(key, {})
        if not prev or (ev.get("ts") or "") > (prev.get("ts") or ""):
            by_key[key] = ev

    results: List[SessionHealth] = []
    for (src, acc, proxy), ev in by_key.items():
        cookie_path = COOKIES_DIR / f"{src}__{acc}__{proxy}.json"
        results.append(
            SessionHealth(
                source=src or "",
                account_id=acc or "",
                proxy_id=proxy or "",
                has_cookie_file=cookie_path.exists(),
                last_seen_at=ev.get("ts"),
                last_event_type=ev.get("event_type"),
            )
        )

    return results


def summarize_session_health(source: Optional[str] = None) -> Dict[str, int]:
    health = get_session_health(source)
    total = len(health)
    with_cookies = sum(1 for h in health if h.has_cookie_file)
    return {
        "total_bindings": total,
        "with_cookies": with_cookies,
        "without_cookies": total - with_cookies,
    }


__all__ = ["SessionHealth", "get_session_health", "summarize_session_health"]
