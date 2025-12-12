"""
Date Utilities Module

Common date and time operations.

Author: Scraper Platform Team
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def parse_date(date_string: str, formats: Optional[list] = None) -> Optional[datetime]:
    """
    Parse date string with multiple format attempts.

    Args:
        date_string: Date string to parse
        formats: List of formats to try

    Returns:
        Parsed datetime or None
    """
    if formats is None:
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%Y"
        ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_string}")
    return None


def format_date(dt: datetime, format_string: str = "%Y-%m-%d") -> str:
    """
    Format datetime to string.

    Args:
        dt: Datetime to format
        format_string: Format string

    Returns:
        Formatted date string
    """
    return dt.strftime(format_string)


def get_date_range(start: datetime, end: datetime, step: timedelta = timedelta(days=1)) -> list:
    """
    Generate date range.

    Args:
        start: Start date
        end: End date
        step: Step size

    Returns:
        List of dates
    """
    dates = []
    current = start

    while current <= end:
        dates.append(current)
        current += step

    return dates


def is_expired(timestamp: datetime, ttl_seconds: int) -> bool:
    """
    Check if timestamp is expired.

    Args:
        timestamp: Timestamp to check
        ttl_seconds: Time to live in seconds

    Returns:
        True if expired
    """
    age = (datetime.now() - timestamp).total_seconds()
    return age > ttl_seconds
