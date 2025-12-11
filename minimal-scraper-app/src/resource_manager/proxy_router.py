import os
import random
from typing import Optional

from src.common.logging_utils import get_logger

log = get_logger("proxy-router")


def pick_healthy_proxy(source: str) -> Optional[str]:
    """Pick a healthy proxy for the given source."""
    env_key = f"{source.upper()}_PROXIES"
    raw = os.getenv(env_key, "").strip()
    if not raw:
        log.info("No proxies configured via %s; running direct.", env_key)
        return None
    proxies = [p.strip() for p in raw.split(",") if p.strip()]
    proxy = random.choice(proxies)
    log.info("Chose proxy %s for %s", proxy, source)
    return proxy
