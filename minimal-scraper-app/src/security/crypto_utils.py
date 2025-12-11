import json
import os
from functools import lru_cache
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken

from src.common.logging_utils import get_logger


log = get_logger(__name__)


_KEY_ENV = "SCRAPER_SECRET_KEY"
_FERNET: Fernet | None = None


def _get_fernet() -> Fernet:
    """
    Return a global Fernet instance.

    SCRAPER_SECRET_KEY must be a 32-byte urlsafe base64-encoded key.
    Generate via:
        from cryptography.fernet import Fernet
        print(Fernet.generate_key().decode())
    """
    global _FERNET
    if _FERNET is not None:
        return _FERNET

    raw = os.getenv(_KEY_ENV)
    if not raw:
        raise RuntimeError(
            f"{_KEY_ENV} is not set; cannot encrypt/decrypt sensitive data"
        )

    try:
        _FERNET = Fernet(raw.encode("ascii"))
    except Exception as exc:
        raise RuntimeError(f"Invalid {_KEY_ENV} value") from exc

    return _FERNET


def encrypt_json(data: Dict[str, Any]) -> bytes:
    """
    Serialize dict → JSON → encrypt → bytes.
    """
    f = _get_fernet()
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f.encrypt(raw)


def decrypt_json(blob: bytes) -> Dict[str, Any]:
    """
    Decrypt bytes → JSON → dict.
    """
    f = _get_fernet()
    try:
        raw = f.decrypt(blob)
    except InvalidToken as exc:
        log.error(
            "Failed to decrypt JSON blob; invalid token", extra={"error": str(exc)}
        )
        raise

    return json.loads(raw.decode("utf-8"))
