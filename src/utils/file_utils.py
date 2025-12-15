"""
File Utilities Module

Common file operations and utilities.

Author: Scraper Platform Team
"""

import logging
from pathlib import Path
from typing import List
import json

logger = logging.getLogger(__name__)


def ensure_dir(path: Path) -> None:
    """
    Ensure directory exists.

    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)


def read_json(file_path: Path) -> dict:
    """
    Read JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data
    """
    with open(file_path, 'r') as f:
        return json.load(f)


def write_json(file_path: Path, data: dict, indent: int = 2) -> None:
    """
    Write JSON file.

    Args:
        file_path: Path to write
        data: Data to write
        indent: JSON indentation
    """
    ensure_dir(file_path.parent)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=indent)


def list_files(directory: Path, pattern: str = "*") -> List[Path]:
    """
    List files in directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern

    Returns:
        List of file paths
    """
    return list(directory.glob(pattern))


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: File path

    Returns:
        File size in bytes
    """
    return file_path.stat().st_size if file_path.exists() else 0
