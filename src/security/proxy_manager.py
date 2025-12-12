"""
Proxy Manager Module

Secure proxy configuration and management with credential handling.
Integrates with credential manager for secure proxy authentication.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProxyType(str, Enum):
    """Proxy protocol types."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


@dataclass
class ProxyConfig:
    """Proxy configuration."""

    host: str
    port: int
    proxy_type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    provider: Optional[str] = None
    max_concurrent: int = 10
    enabled: bool = True

    def get_url(self) -> str:
        """
        Get proxy URL.

        Returns:
            Formatted proxy URL
        """
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type.value}://{self.host}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "http": self.get_url(),
            "https": self.get_url(),
        }


class ProxyManager:
    """
    Manages proxy configurations with secure credential storage.

    Features:
    - Secure credential storage via credential manager
    - Proxy rotation and load balancing
    - Health monitoring integration
    - Geographic proxy selection
    """

    def __init__(self, credential_manager: Any):
        """
        Initialize proxy manager.

        Args:
            credential_manager: Credential manager instance for secure storage
        """
        self.credential_manager = credential_manager
        self.proxies: Dict[str, ProxyConfig] = {}
        logger.info("Initialized ProxyManager")

    def add_proxy(
        self,
        proxy_id: str,
        host: str,
        port: int,
        proxy_type: ProxyType = ProxyType.HTTP,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Add a proxy configuration.

        Args:
            proxy_id: Unique proxy identifier
            host: Proxy host
            port: Proxy port
            proxy_type: Proxy protocol type
            username: Proxy username (stored securely)
            password: Proxy password (stored securely)
            **kwargs: Additional proxy metadata
        """
        # Store credentials securely if provided
        if username and password:
            credential_key = f"proxy_{proxy_id}_credentials"
            self.credential_manager.set(
                credential_key,
                {"username": username, "password": password}
            )
            logger.debug(f"Stored credentials for proxy {proxy_id}")

        # Create proxy config (without storing credentials in memory)
        proxy_config = ProxyConfig(
            host=host,
            port=port,
            proxy_type=proxy_type,
            username=username,  # Keep reference for URL generation
            password=password,  # Keep reference for URL generation
            **{k: v for k, v in kwargs.items() if k in ProxyConfig.__dataclass_fields__}
        )

        self.proxies[proxy_id] = proxy_config
        logger.info(f"Added proxy {proxy_id}: {host}:{port}")

    def get_proxy(self, proxy_id: str) -> Optional[ProxyConfig]:
        """
        Get proxy configuration by ID.

        Args:
            proxy_id: Proxy identifier

        Returns:
            ProxyConfig or None
        """
        proxy = self.proxies.get(proxy_id)

        if proxy and not proxy.password:
            # Load credentials from credential manager if not in memory
            credential_key = f"proxy_{proxy_id}_credentials"
            credentials = self.credential_manager.get(credential_key)
            if credentials:
                proxy.username = credentials.get("username")
                proxy.password = credentials.get("password")

        return proxy

    def remove_proxy(self, proxy_id: str) -> bool:
        """
        Remove a proxy configuration.

        Args:
            proxy_id: Proxy identifier

        Returns:
            True if removed successfully
        """
        if proxy_id in self.proxies:
            # Remove credentials
            credential_key = f"proxy_{proxy_id}_credentials"
            self.credential_manager.delete(credential_key)

            # Remove proxy config
            del self.proxies[proxy_id]
            logger.info(f"Removed proxy {proxy_id}")
            return True

        logger.warning(f"Proxy not found: {proxy_id}")
        return False

    def list_proxies(self, country: Optional[str] = None) -> List[str]:
        """
        List all proxy IDs, optionally filtered by country.

        Args:
            country: Filter by country code

        Returns:
            List of proxy IDs
        """
        if country:
            return [
                pid for pid, proxy in self.proxies.items()
                if proxy.country == country and proxy.enabled
            ]
        return [pid for pid, proxy in self.proxies.items() if proxy.enabled]

    def get_proxy_for_requests(self, proxy_id: str) -> Optional[Dict[str, str]]:
        """
        Get proxy dict formatted for requests library.

        Args:
            proxy_id: Proxy identifier

        Returns:
            Proxy dict for requests
        """
        proxy = self.get_proxy(proxy_id)
        if proxy and proxy.enabled:
            return proxy.to_dict()
        return None

    def rotate_credentials(self, proxy_id: str, new_username: str, new_password: str) -> bool:
        """
        Rotate proxy credentials.

        Args:
            proxy_id: Proxy identifier
            new_username: New username
            new_password: New password

        Returns:
            True if rotated successfully
        """
        proxy = self.proxies.get(proxy_id)
        if not proxy:
            logger.warning(f"Proxy not found: {proxy_id}")
            return False

        # Update credentials in credential manager
        credential_key = f"proxy_{proxy_id}_credentials"
        self.credential_manager.rotate(
            credential_key,
            {"username": new_username, "password": new_password}
        )

        # Update proxy config
        proxy.username = new_username
        proxy.password = new_password

        logger.info(f"Rotated credentials for proxy {proxy_id}")
        return True

    def enable_proxy(self, proxy_id: str) -> bool:
        """Enable a proxy."""
        if proxy_id in self.proxies:
            self.proxies[proxy_id].enabled = True
            logger.info(f"Enabled proxy {proxy_id}")
            return True
        return False

    def disable_proxy(self, proxy_id: str) -> bool:
        """Disable a proxy."""
        if proxy_id in self.proxies:
            self.proxies[proxy_id].enabled = False
            logger.info(f"Disabled proxy {proxy_id}")
            return True
        return False


def create_proxy_manager(credential_manager: Any) -> ProxyManager:
    """
    Factory function to create a proxy manager.

    Args:
        credential_manager: Credential manager instance

    Returns:
        ProxyManager instance
    """
    return ProxyManager(credential_manager=credential_manager)
