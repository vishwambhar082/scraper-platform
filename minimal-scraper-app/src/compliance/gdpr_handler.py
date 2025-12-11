"""
Utilities for GDPR/PII scrubbing.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s\-\(\)]{7,}\d")


class GdprHandler:
    def scrub_record(self, record: Dict[str, object]) -> Dict[str, object]:
        cleaned = {}
        for key, value in record.items():
            if not isinstance(value, str):
                cleaned[key] = value
                continue

            redacted = EMAIL_RE.sub("[redacted-email]", value)
            redacted = PHONE_RE.sub("[redacted-phone]", redacted)
            cleaned[key] = redacted
        return cleaned

    def scrub_records(self, records: Iterable[Dict[str, object]]) -> Iterable[Dict[str, object]]:
        for record in records:
            yield self.scrub_record(record)

