"""
XML Parser Module

Parses XML data with error handling.

Author: Scraper Platform Team
"""

import logging
from typing import Any, Dict
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class XMLParser:
    """Parses XML data."""

    def __init__(self):
        """Initialize XML parser."""
        logger.debug("Initialized XMLParser")

    def parse(self, xml_string: str) -> ET.Element:
        """
        Parse XML string.

        Args:
            xml_string: XML string to parse

        Returns:
            Root element
        """
        try:
            return ET.fromstring(xml_string)
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            raise

    def to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary."""
        result = {"tag": element.tag}

        if element.text and element.text.strip():
            result["text"] = element.text.strip()

        if element.attrib:
            result["attributes"] = element.attrib

        children = list(element)
        if children:
            result["children"] = [self.to_dict(child) for child in children]

        return result
