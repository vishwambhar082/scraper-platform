"""
Monitor website terms-of-service pages for changes.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict

import requests


@dataclass
class TermsMonitor:
    cache: Dict[str, str] = field(default_factory=dict)

    def fetch_hash(self, url: str) -> str:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        digest = hashlib.sha256(response.text.encode("utf-8")).hexdigest()
        return digest

    def has_changed(self, url: str) -> bool:
        new_hash = self.fetch_hash(url)
        old_hash = self.cache.get(url)
        self.cache[url] = new_hash
        return old_hash is not None and old_hash != new_hash

