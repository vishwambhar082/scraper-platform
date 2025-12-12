"""
JSON Parser Module

Parses JSON data with error handling and validation.

Author: Scraper Platform Team
"""

import logging
import json
from typing import Any, Dict

logger = logging.getLogger(__name__)


class JSONParser:
    """Parses JSON data."""

    def __init__(self, strict: bool = False):
        """Initialize JSON parser."""
        self.strict = strict
        logger.debug("Initialized JSONParser")

    def parse(self, json_string: str) -> Any:
        """
        Parse JSON string.

        Args:
            json_string: JSON string to parse

        Returns:
            Parsed data
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            if self.strict:
                raise
            return None

    def parse_file(self, file_path: str) -> Any:
        """Parse JSON file."""
        with open(file_path, 'r') as f:
            return self.parse(f.read())
