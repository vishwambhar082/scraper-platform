# src/resource_manager/proxy_site_health.py

from dataclasses import dataclass
from typing import Dict, Tuple
import threading

from src.common.logging_utils import get_logger

log = get_logger("proxy-site-health")


@dataclass
class ProxySiteStatus:
    blocked: bool = False
    last_error: str | None = None


_STATUS: Dict[Tuple[str, str], ProxySiteStatus] = {}  # (proxy, hostname) -> status
_LOCK = threading.Lock()


def mark_blocked(proxy: str, hostname: str, reason: str | None = None) -> None:
    key = (proxy, hostname)
    with _LOCK:
        st = _STATUS.setdefault(key, ProxySiteStatus())
        st.blocked = True
        st.last_error = reason
    log.warning("Proxy %s blocked for %s (reason=%s)", proxy, hostname, reason)


def mark_healthy(proxy: str, hostname: str) -> None:
    key = (proxy, hostname)
    with _LOCK:
        st = _STATUS.setdefault(key, ProxySiteStatus())
        was_blocked = st.blocked
        st.blocked = False
        st.last_error = None
    if was_blocked:
        log.info("Proxy %s unblocked for %s", proxy, hostname)


def is_blocked(proxy: str, hostname: str) -> bool:
    return _STATUS.get((proxy, hostname), ProxySiteStatus()).blocked
