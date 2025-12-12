"""
PCID Manager Module

Manages Product Canonical IDs for deduplication and matching.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, Optional, List
import hashlib

logger = logging.getLogger(__name__)


class PCIDManager:
    """
    Manages Product Canonical IDs.

    Features:
    - PCID generation
    - Product matching
    - Deduplication
    """

    def __init__(self):
        """Initialize PCID manager."""
        self.pcid_index: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized PCIDManager")

    def generate_pcid(self, product_data: Dict[str, Any]) -> str:
        """
        Generate PCID for a product.

        Args:
            product_data: Product data

        Returns:
            PCID string
        """
        # Create hash from key fields
        key_fields = [
            str(product_data.get("name", "")),
            str(product_data.get("url", "")),
            str(product_data.get("company", ""))
        ]

        combined = "|".join(key_fields).lower()
        hash_obj = hashlib.sha256(combined.encode())
        pcid = f"PCID_{hash_obj.hexdigest()[:16]}"

        return pcid

    def match_product(
        self,
        product_data: Dict[str, Any],
        threshold: float = 0.8
    ) -> Optional[str]:
        """
        Match product to existing PCID.

        Args:
            product_data: Product data
            threshold: Matching threshold

        Returns:
            Matched PCID or None
        """
        # Generate PCID for new product
        pcid = self.generate_pcid(product_data)

        # Check if exists
        if pcid in self.pcid_index:
            return pcid

        # No match found
        return None

    def register_product(self, pcid: str, product_data: Dict[str, Any]) -> None:
        """Register product with PCID."""
        self.pcid_index[pcid] = product_data
        logger.debug(f"Registered PCID: {pcid}")
