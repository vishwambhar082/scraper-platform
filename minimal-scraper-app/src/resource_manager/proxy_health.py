# src/resource_manager/proxy_health.py

from dataclasses import dataclass
from typing import Dict, Tuple
import threading

from src.common.logging_utils import get_logger

log = get_logger("proxy-health")


@dataclass
class ProxyHealth:
    successes: int = 0
    failures: int = 0

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def failure_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.failures / self.total


_HEALTH: Dict[Tuple[str, str], ProxyHealth] = {}  # (source, proxy) -> health
_LOCK = threading.Lock()


def record_success(source: str, proxy: str) -> None:
    key = (source, proxy)
    with _LOCK:
        ph = _HEALTH.setdefault(key, ProxyHealth())
        ph.successes += 1
        log.debug("Proxy success %s/%s -> %s", source, proxy, ph)


def record_failure(source: str, proxy: str) -> None:
    key = (source, proxy)
    with _LOCK:
        ph = _HEALTH.setdefault(key, ProxyHealth())
        ph.failures += 1
        log.debug("Proxy failure %s/%s -> %s", source, proxy, ph)


def get_health(source: str, proxy: str) -> ProxyHealth:
    return _HEALTH.setdefault((source, proxy), ProxyHealth())
