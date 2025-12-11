"""
Google Cloud Storage exporter utilities.

Provides a minimal wrapper around ``google-cloud-storage`` to push processed
records directly into a bucket.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Iterable, Mapping, Optional


def export_to_gcs(
    records: Iterable[Mapping[str, object]],
    *,
    bucket: str,
    prefix: str | None = None,
    object_name: Optional[str] = None,
) -> str:
    """
    Upload records as a CSV object to Google Cloud Storage.

    Args:
        records: Iterable of record mappings to serialize.
        bucket: Destination GCS bucket name.
        prefix: Optional key prefix (``"folder/"`` style) to prepend.
        object_name: Optional object name; defaults to ``export.csv`` when not
            provided.

    Returns:
        The full object key uploaded to GCS.

    Raises:
        google.cloud.exceptions.GoogleCloudError for upload failures.
        ImportError if ``google-cloud-storage`` is not installed.
    """

    rows = list(records)
    if not rows:
        return ""

    from google.cloud import storage

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

    client = storage.Client()
    bucket_obj = client.bucket(bucket)
    blob = bucket_obj.blob(full_key)
    blob.upload_from_string(buffer.getvalue(), content_type="text/csv")

    return full_key


__all__ = ["export_to_gcs"]
