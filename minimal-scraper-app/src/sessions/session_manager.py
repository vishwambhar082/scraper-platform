import base64
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from src.common.logging_utils import get_logger
from src.common.paths import COOKIES_DIR, SESSION_LOGS_DIR
from src.security.crypto_utils import decrypt_json, encrypt_json

log = get_logger("session-manager")


@dataclass
class SessionRecord:
    source: str
    account_id: str
    proxy_id: str
    cookies_path: Path
    last_seen_at: Optional[str] = None

    def try_restore_cookies(self, driver) -> bool:
        """Attempt to restore cookies from disk to the driver."""
        if not self.cookies_path.exists():
            log.info("No cookies file for %s:%s", self.source, self.account_id)
            return False
        try:
            cookies = load_session_cookies(self.source, self.account_id, self.proxy_id) or []
            for c in cookies:
                driver.add_cookie(c)
            log.info("Restored %d cookies for %s:%s", len(cookies), self.source, self.account_id)
            return True
        except OSError as exc:
            log.warning(
                "Failed to restore cookies due to invalid file: %s",
                exc,
                extra={"path": str(self.cookies_path)},
            )
            return False

    def save_cookies(self, driver) -> None:
        """Save cookies from the driver to disk."""
        try:
            cookies = driver.get_cookies()
            save_session_cookies(self.source, self.account_id, self.proxy_id, cookies)
            self.last_seen_at = datetime.utcnow().isoformat()
            self._log_event("cookies_saved", {"count": len(cookies)})
        except RuntimeError:
            raise
        except (TypeError, OSError, json.JSONDecodeError) as exc:
            log.warning(
                "Failed to serialize cookies", extra={"error": str(exc), "path": str(self.cookies_path)}
            )
        except Exception as exc:
            log.warning(
                "Unexpected error saving cookies", extra={"error": str(exc), "path": str(self.cookies_path)}
            )

    def _log_event(self, event_type: str, extra: Dict[str, Any]) -> None:
        """Log a session event to the session events log file."""
        SESSION_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        ev = {
            "ts": datetime.utcnow().isoformat(),
            "source": self.source,
            "account_id": self.account_id,
            "proxy_id": self.proxy_id,
            "event_type": event_type,
            "extra": extra,
        }
        log_path = SESSION_LOGS_DIR / "session_events.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev) + "\n")


def _encode_component(component: str) -> str:
    """Encode path components to avoid delimiter collisions and unsafe chars."""

    if not component:
        return "none"

    encoded = base64.urlsafe_b64encode(component.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def create_session_record(source: str, account_id: str, proxy_id: str) -> SessionRecord:
    """
    Factory to create a SessionRecord with a safe cookie filename.

    We base64-url-safe encode each component to avoid collisions when raw values
    contain "__" or filesystem-unfriendly characters.
    """
    encoded_source = _encode_component(source)
    encoded_account = _encode_component(account_id)
    encoded_proxy = _encode_component(proxy_id)
    cookie_file = COOKIES_DIR / f"{encoded_source}__{encoded_account}__{encoded_proxy}.json"
    return SessionRecord(source=source, account_id=account_id, proxy_id=proxy_id, cookies_path=cookie_file)


def save_session_cookies(source: str, account_id: str, proxy_id: str, cookies: Dict[str, Any]) -> None:
    record = create_session_record(source, account_id, proxy_id)
    record.cookies = cookies
    payload = {"source": source, "account_id": account_id, "proxy_id": proxy_id, "cookies": cookies}
    blob = encrypt_json(payload)
    with open(record.cookies_path, "wb") as f:
        f.write(blob)


def load_session_cookies(source: str, account_id: str, proxy_id: str) -> Optional[Dict[str, Any]]:
    record = create_session_record(source, account_id, proxy_id)
    if not record.cookies_path.exists():
        return None
    with open(record.cookies_path, "rb") as f:
        blob = f.read()
    payload = decrypt_json(blob)
    record.cookies = payload.get("cookies") or {}
    return record.cookies
