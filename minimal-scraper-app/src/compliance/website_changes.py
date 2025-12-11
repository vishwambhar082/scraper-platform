"""
Detects structural website changes by hashing DOM snapshots.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict

import requests


@dataclass
class WebsiteChangeDetector:
    fingerprints: Dict[str, str] = field(default_factory=dict)

    def snapshot(self, url: str) -> str:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        digest = hashlib.sha256(response.content).hexdigest()
        return digest

    def has_changed(self, url: str) -> bool:
        digest = self.snapshot(url)
        previous = self.fingerprints.get(url)
        self.fingerprints[url] = digest
        return previous is not None and previous != digest

