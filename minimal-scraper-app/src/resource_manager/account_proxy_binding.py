# src/resource_manager/account_proxy_binding.py

import json
from pathlib import Path
from typing import Dict, Optional

from src.common.logging_utils import get_logger
from src.common.paths import SESSIONS_DIR

log = get_logger("account-proxy-binding")

_BINDINGS_FILE: Path = SESSIONS_DIR / "account_proxy_binding.json"
_BINDINGS_CACHE: Dict[str, Dict[str, str]] = {}
_LOADED = False


def _load() -> None:
    """Load bindings from disk into memory."""
    global _LOADED, _BINDINGS_CACHE
    if _LOADED:
        return
    if _BINDINGS_FILE.exists():
        try:
            data = json.loads(_BINDINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _BINDINGS_CACHE = {
                    str(source): {str(acc): str(proxy) for acc, proxy in mapping.items()}
                    for source, mapping in data.items()
                }
            log.info("Loaded %d sources of bindings from %s", len(_BINDINGS_CACHE), _BINDINGS_FILE)
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to load account-proxy bindings: %s", exc)
            _BINDINGS_CACHE = {}
    else:
        _BINDINGS_CACHE = {}
    _LOADED = True


def _persist() -> None:
    """Persist in-memory bindings to disk (best-effort)."""
    try:
        _BINDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BINDINGS_FILE.write_text(json.dumps(_BINDINGS_CACHE, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to persist account-proxy bindings: %s", exc)


def get_binding(source: str, account_id: str) -> Optional[str]:
    """Return the proxy_id bound to (source, account_id), if any."""
    _load()
    return _BINDINGS_CACHE.get(source, {}).get(account_id)


def set_binding(source: str, account_id: str, proxy_id: str) -> None:
    """Bind account_id for a given source to a specific proxy_id."""
    _load()
    mapping = _BINDINGS_CACHE.setdefault(source, {})
    old = mapping.get(account_id)
    mapping[account_id] = proxy_id
    _persist()
    log.info("Binding set: %s/%s -> %s (was: %s)", source, account_id, proxy_id, old)


def clear_binding(source: str, account_id: str) -> None:
    """Remove an existing binding for (source, account_id)."""
    _load()
    if source in _BINDINGS_CACHE and account_id in _BINDINGS_CACHE[source]:
        _BINDINGS_CACHE[source].pop(account_id, None)
        if not _BINDINGS_CACHE[source]:
            _BINDINGS_CACHE.pop(source, None)
        _persist()
        log.info("Binding cleared: %s/%s", source, account_id)


def get_or_create_binding(source: str, account_id: str, default_proxy: Optional[str]) -> Optional[str]:
    """
    Get existing binding or create one with default_proxy.

    If default_proxy is None and no binding exists, returns None.
    """
    current = get_binding(source, account_id)
    if current is not None:
        return current
    if default_proxy is None:
        return None
    set_binding(source, account_id, default_proxy)
    return default_proxy
