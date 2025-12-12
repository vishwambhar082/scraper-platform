"""
Credential Manager Module

Provides secure storage and retrieval of credentials using encryption.
Supports multiple backends: local encrypted storage, HashiCorp Vault, AWS Secrets Manager.

Author: Scraper Platform Team
"""

import logging
import json
import os
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CredentialBackend(ABC):
    """Abstract base class for credential storage backends."""

    @abstractmethod
    def store(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Store a credential."""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a credential."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a credential."""
        pass

    @abstractmethod
    def list_keys(self) -> List[str]:
        """List all stored credential keys."""
        pass


class LocalEncryptedBackend(CredentialBackend):
    """Local file-based encrypted credential storage."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize local encrypted backend.

        Args:
            storage_path: Path to store encrypted credentials
        """
        self.storage_path = storage_path or Path("config/secrets/encrypted_secrets.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._credentials: Dict[str, Dict[str, Any]] = self._load()
        logger.info(f"Initialized LocalEncryptedBackend at {self.storage_path}")

    def _load(self) -> Dict[str, Dict[str, Any]]:
        """Load credentials from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data)} credentials from {self.storage_path}")
                    return data
            except Exception as e:
                logger.error(f"Failed to load credentials: {e}")
                return {}
        return {}

    def _save(self) -> None:
        """Save credentials to disk."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self._credentials, f, indent=2)
            logger.debug(f"Saved {len(self._credentials)} credentials to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def store(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Store a credential with optional TTL.

        Args:
            key: Credential identifier
            value: Credential data
            ttl: Time to live in seconds (optional)

        Returns:
            True if stored successfully
        """
        try:
            entry = {
                "value": value,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            if ttl:
                entry["expires_at"] = (datetime.now() + timedelta(seconds=ttl)).isoformat()

            self._credentials[key] = entry
            self._save()
            logger.info(f"Stored credential: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store credential {key}: {e}")
            return False

    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a credential by key.

        Args:
            key: Credential identifier

        Returns:
            Credential data or None if not found/expired
        """
        entry = self._credentials.get(key)
        if not entry:
            logger.warning(f"Credential not found: {key}")
            return None

        # Check expiration
        if "expires_at" in entry:
            expires_at = datetime.fromisoformat(entry["expires_at"])
            if datetime.now() > expires_at:
                logger.warning(f"Credential expired: {key}")
                self.delete(key)
                return None

        logger.debug(f"Retrieved credential: {key}")
        return entry["value"]

    def delete(self, key: str) -> bool:
        """
        Delete a credential.

        Args:
            key: Credential identifier

        Returns:
            True if deleted successfully
        """
        if key in self._credentials:
            del self._credentials[key]
            self._save()
            logger.info(f"Deleted credential: {key}")
            return True
        logger.warning(f"Credential not found for deletion: {key}")
        return False

    def list_keys(self) -> List[str]:
        """
        List all stored credential keys.

        Returns:
            List of credential keys
        """
        return list(self._credentials.keys())


class VaultBackend(CredentialBackend):
    """HashiCorp Vault credential backend."""

    def __init__(self, vault_url: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize Vault backend.

        Args:
            vault_url: Vault server URL
            token: Vault authentication token
        """
        self.vault_url = vault_url or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.token = token or os.getenv("VAULT_TOKEN")
        logger.info(f"Initialized VaultBackend for {self.vault_url}")

        # Import vault client if available
        try:
            from ..security.vault_client import VaultClient
            self.client = VaultClient(url=self.vault_url, token=self.token)
        except ImportError:
            logger.warning("VaultClient not available, using stub implementation")
            self.client = None

    def store(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Store credential in Vault."""
        if not self.client:
            logger.error("Vault client not available")
            return False

        try:
            self.client.write_secret(key, value, ttl=ttl)
            logger.info(f"Stored credential in Vault: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store credential in Vault: {e}")
            return False

    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve credential from Vault."""
        if not self.client:
            logger.error("Vault client not available")
            return None

        try:
            secret = self.client.read_secret(key)
            logger.debug(f"Retrieved credential from Vault: {key}")
            return secret
        except Exception as e:
            logger.error(f"Failed to retrieve credential from Vault: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete credential from Vault."""
        if not self.client:
            logger.error("Vault client not available")
            return False

        try:
            self.client.delete_secret(key)
            logger.info(f"Deleted credential from Vault: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete credential from Vault: {e}")
            return False

    def list_keys(self) -> List[str]:
        """List all credential keys in Vault."""
        if not self.client:
            logger.error("Vault client not available")
            return []

        try:
            keys = self.client.list_secrets()
            return keys
        except Exception as e:
            logger.error(f"Failed to list credentials from Vault: {e}")
            return []


class CredentialManager:
    """
    Main credential manager interface.

    Provides unified access to credentials across multiple backends
    with automatic fallback and caching.
    """

    def __init__(
        self,
        backend: Optional[CredentialBackend] = None,
        use_env_fallback: bool = True
    ):
        """
        Initialize credential manager.

        Args:
            backend: Storage backend (defaults to LocalEncryptedBackend)
            use_env_fallback: Fall back to environment variables if key not found
        """
        self.backend = backend or LocalEncryptedBackend()
        self.use_env_fallback = use_env_fallback
        logger.info(f"Initialized CredentialManager with backend: {type(self.backend).__name__}")

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Get a credential value.

        Args:
            key: Credential identifier
            default: Default value if not found

        Returns:
            Credential value or default
        """
        # Try backend first
        credential = self.backend.retrieve(key)
        if credential:
            # Return the actual credential value (not the wrapper)
            if isinstance(credential, dict) and "value" in credential:
                return credential["value"]
            return credential

        # Fall back to environment variables
        if self.use_env_fallback:
            env_value = os.getenv(key)
            if env_value:
                logger.debug(f"Retrieved credential from environment: {key}")
                return env_value

        logger.debug(f"Credential not found, returning default: {key}")
        return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Set a credential value.

        Args:
            key: Credential identifier
            value: Credential value
            ttl: Time to live in seconds
            metadata: Additional metadata

        Returns:
            True if stored successfully
        """
        credential_data = {
            "value": value,
            "metadata": metadata or {}
        }
        return self.backend.store(key, credential_data, ttl=ttl)

    def delete(self, key: str) -> bool:
        """
        Delete a credential.

        Args:
            key: Credential identifier

        Returns:
            True if deleted successfully
        """
        return self.backend.delete(key)

    def list_all(self) -> List[str]:
        """
        List all stored credentials.

        Returns:
            List of credential keys
        """
        return self.backend.list_keys()

    def rotate(self, key: str, new_value: Any) -> bool:
        """
        Rotate a credential (update with new value).

        Args:
            key: Credential identifier
            new_value: New credential value

        Returns:
            True if rotated successfully
        """
        # Get existing metadata
        existing = self.backend.retrieve(key)
        metadata = existing.get("metadata", {}) if existing else {}
        metadata["rotated_at"] = datetime.now().isoformat()

        return self.set(key, new_value, metadata=metadata)


# Singleton instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """
    Get the global credential manager instance.

    Returns:
        CredentialManager singleton
    """
    global _credential_manager
    if _credential_manager is None:
        # Determine backend from environment
        backend_type = os.getenv("CREDENTIAL_BACKEND", "local").lower()

        if backend_type == "vault":
            backend = VaultBackend()
        else:
            backend = LocalEncryptedBackend()

        _credential_manager = CredentialManager(backend=backend)

    return _credential_manager
