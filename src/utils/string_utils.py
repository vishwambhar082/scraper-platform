"""
String Utilities Module

Common string operations and transformations.

Author: Scraper Platform Team
"""

import logging
import re

logger = logging.getLogger(__name__)


def clean_whitespace(text: str) -> str:
    """
    Clean and normalize whitespace.

    Args:
        text: Input text

    Returns:
        Cleaned text
    """
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.

    Args:
        text: Text to slugify

    Returns:
        Slugified text
    """
    # Convert to lowercase
    text = text.lower()

    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)

    # Remove special characters
    text = re.sub(r'[^a-z0-9-]', '', text)

    # Remove multiple hyphens
    text = re.sub(r'-+', '-', text)

    return text.strip('-')


def extract_numbers(text: str) -> list:
    """
    Extract all numbers from text.

    Args:
        text: Input text

    Returns:
        List of numbers as floats
    """
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    return [float(m) for m in matches]


def remove_html_tags(html: str) -> str:
    """
    Remove HTML tags from text.

    Args:
        html: HTML text

    Returns:
        Plain text
    """
    clean = re.sub(r'<[^>]+>', '', html)
    return clean_whitespace(clean)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    return filename
