import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken

from src.common.logging_utils import get_logger


log = get_logger(__name__)


_KEY_ENV = "SCRAPER_SECRET_KEY"
_KEY_FILE_ENV = "SCRAPER_SECRET_KEY_FILE"
_DEFAULT_KEY_PATH = Path(__file__).resolve().parents[2] / "config" / "secrets" / "scraper_secret.key"
_FERNET: Fernet | None = None


def _load_or_create_key() -> str:
    """
    Load the Fernet key from env, then optional file, otherwise generate + persist.
    """
    env_val = os.getenv(_KEY_ENV)
    if env_val:
        return env_val

    key_path = Path(os.getenv(_KEY_FILE_ENV, _DEFAULT_KEY_PATH))
    if key_path.exists():
        try:
            return key_path.read_text(encoding="ascii").strip()
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Failed to read key file; regenerating a new key", extra={"path": str(key_path), "error": str(exc)})

    key_path.parent.mkdir(parents=True, exist_ok=True)
    new_key = Fernet.generate_key().decode("ascii")
    try:
        key_path.write_text(new_key, encoding="ascii")
        try:
            key_path.chmod(0o600)
        except Exception:
            # Best effort on non-POSIX filesystems (e.g., Windows)
            pass
        log.warning(
            "Generated SCRAPER_SECRET_KEY automatically and saved to file; set env for consistency.",
            extra={"path": str(key_path)},
        )
    except Exception as exc:  # pragma: no cover - defensive
        log.error("Failed to persist generated key; using in-memory only", extra={"path": str(key_path), "error": str(exc)})
    return new_key


def _get_fernet() -> Fernet:
    """
    Return a global Fernet instance.
    
    Falls back to generating and persisting a key when SCRAPER_SECRET_KEY is not set.
    """
    global _FERNET
    if _FERNET is not None:
        return _FERNET

    raw = _load_or_create_key()

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
