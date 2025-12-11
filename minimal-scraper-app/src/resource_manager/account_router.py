import os
import threading
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple

from src.common.logging_utils import get_logger, safe_log
from src.observability import metrics
from src.resource_manager.settings import get_rate_limit_settings

log = get_logger("account-router")


@dataclass
class AccountStats:
    successes: int = 0
    failures: int = 0

    @property
    def error_rate(self) -> float:
        total = self.successes + self.failures
        return (self.failures / total) if total else 0.0


class AccountRouter:
    """Per-instance account router to avoid global caches."""

    def __init__(self, settings: Optional[Mapping[str, object]] = None):
        self._settings = settings or {}
        self._accounts_cache: Dict[str, Dict[str, Tuple[str, str]]] = {}
        self._account_index: Dict[str, int] = {}
        self._account_stats: Dict[str, Dict[str, AccountStats]] = {}
        self._account_gates: Dict[str, threading.BoundedSemaphore] = {}
        self._account_lock = threading.Lock()

    def _parse_account_key(self, account_key: str) -> Tuple[str, str]:
        source, sep, account_id = account_key.partition(":")
        if sep:
            return source, account_id

        safe_log(
            log,
            "warning",
            "account_key_missing_separator",
            {"account_key": account_key},
        )
        return account_key, account_key

    def _get_accounts_from_settings(self, source: str) -> Optional[Dict[str, Tuple[str, str]]]:
        if not isinstance(self._settings, Mapping):
            return None

        accounts_cfg = self._settings.get("accounts")
        if isinstance(accounts_cfg, Mapping):
            accounts = accounts_cfg.get(source)
            if isinstance(accounts, Mapping):
                return {k: tuple(v) for k, v in accounts.items()}  # type: ignore[misc]

        source_cfg = self._settings.get(source)
        if isinstance(source_cfg, Mapping):
            accounts = source_cfg.get("accounts")
            if isinstance(accounts, Mapping):
                return {k: tuple(v) for k, v in accounts.items()}  # type: ignore[misc]

        return None

    def _load_accounts_from_env(self, source: str) -> Dict[str, Tuple[str, str]]:
        prefix = source.upper()
        idx = 1
        accs: Dict[str, Tuple[str, str]] = {}
        while True:
            user = os.getenv(f"{prefix}_USER_{idx}")
            pwd = os.getenv(f"{prefix}_PASS_{idx}")
            if not user or not pwd:
                break
            accs[f"acc{idx}"] = (user, pwd)
            idx += 1
        if not accs:
            raise RuntimeError(f"No accounts configured for source={source}")
        return accs

    def _ensure_accounts_loaded(self, source: str) -> None:
        """
        Thread-safe lazy initialization of account cache and rotation index.
        """

        if source in self._accounts_cache:
            return
        with self._account_lock:
            if source in self._accounts_cache:
                return

            accounts = self._get_accounts_from_settings(source)
            if accounts is None:
                accounts = self._load_accounts_from_env(source)

            self._accounts_cache[source] = accounts
            self._account_index[source] = 0
            rate_limit_settings = get_rate_limit_settings(source)
            max_concurrent = rate_limit_settings.get("max_concurrent") or 0
            if max_concurrent > 0:
                self._account_gates[source] = threading.BoundedSemaphore(max_concurrent)
                safe_log(
                    log,
                    "info",
                    "Initialized account gate from config",
                    {"source": source, "max_concurrent": max_concurrent},
                )

    def acquire_account(self, source: str) -> Tuple[str, str, str]:
        """Acquire an account for the given source."""

        self._ensure_accounts_loaded(source)

        gate = self._account_gates.get(source)
        if gate:
            acquired = gate.acquire(blocking=False)
            if not acquired:
                metrics.incr("rate_limit_hits", source=source)
                gate.acquire()

        accounts = list(self._accounts_cache[source].items())
        if not accounts:
            raise RuntimeError(f"No accounts configured for source={source}")

        with self._account_lock:
            current_idx = self._account_index.get(source, 0)
            acc_id, (user, pwd) = accounts[current_idx % len(accounts)]
            self._account_index[source] = (current_idx + 1) % len(accounts)

        account_key = f"{source}:{acc_id}"
        safe_log(
            log,
            "info",
            "Acquired account",
            {"account_key": account_key, "username": user, "source": source},
        )
        return account_key, user, pwd

    def release_account(self, account_key: str) -> None:
        """Release an account after use."""

        source, _account_id = self._parse_account_key(account_key)
        gate = self._account_gates.get(source)
        if gate:
            try:
                gate.release()
            except ValueError:
                safe_log(
                    log,
                    "warning",
                    "release_without_acquire",
                    {"account_key": account_key, "source": source},
                )
        safe_log(log, "info", f"Released account {account_key}", {"account_key": account_key})

    def mark_account_success(self, account_key: str) -> None:
        """Record a successful use of the account and emit metrics."""

        source, account_id = self._parse_account_key(account_key)
        stats = self._account_stats.setdefault(source, {}).setdefault(account_id, AccountStats())
        stats.successes += 1
        metrics.set_gauge(
            "account_error_rate", stats.error_rate, source=source, account_id=account_id
        )

    def mark_account_error(self, account_key: str) -> None:
        """Record an error for the account and emit error-rate metrics."""

        source, account_id = self._parse_account_key(account_key)
        stats = self._account_stats.setdefault(source, {}).setdefault(account_id, AccountStats())
        stats.failures += 1
        metrics.set_gauge(
            "account_error_rate", stats.error_rate, source=source, account_id=account_id
        )


_DEFAULT_ACCOUNT_ROUTER = AccountRouter()


def get_default_account_router() -> AccountRouter:
    return _DEFAULT_ACCOUNT_ROUTER


def acquire_account(source: str) -> Tuple[str, str, str]:
    return _DEFAULT_ACCOUNT_ROUTER.acquire_account(source)


def release_account(account_key: str) -> None:
    _DEFAULT_ACCOUNT_ROUTER.release_account(account_key)


def mark_account_success(account_key: str) -> None:
    _DEFAULT_ACCOUNT_ROUTER.mark_account_success(account_key)


def mark_account_error(account_key: str) -> None:
    _DEFAULT_ACCOUNT_ROUTER.mark_account_error(account_key)
