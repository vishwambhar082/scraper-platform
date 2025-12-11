"""
S3 exporter utilities.

This module provides a thin wrapper around ``boto3`` to push processed
records directly into an S3 bucket.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Iterable, Mapping, Optional


def export_to_s3(
    records: Iterable[Mapping[str, object]],
    *,
    bucket: str,
    prefix: str | None = None,
    object_name: Optional[str] = None,
) -> str:
    """
    Upload records as a CSV object to S3.

    Args:
        records: Iterable of record mappings to serialize.
        bucket: Destination S3 bucket name.
        prefix: Optional key prefix (``"folder/"`` style) to prepend.
        object_name: Optional object name; defaults to ``export.csv`` when not
            provided.

    Returns:
        The full object key uploaded to S3.

    Raises:
        botocore.exceptions.BotoCoreError or ClientError if the upload fails.
        ImportError if ``boto3`` is not installed.
    """

    rows = list(records)
    if not rows:
        return ""

    import boto3

    object_key = object_name or "export.csv"
    normalized_prefix = prefix or ""
    if normalized_prefix and not normalized_prefix.endswith("/"):
        normalized_prefix = f"{normalized_prefix}/"
    full_key = f"{normalized_prefix}{Path(object_key).name}" if normalized_prefix else Path(object_key).name

    buffer = StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    client = boto3.client("s3")
    client.put_object(Bucket=bucket, Key=full_key, Body=buffer.getvalue().encode("utf-8"))

    return full_key


__all__ = ["export_to_s3"]
