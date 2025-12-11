"""
Generic webhook notifier for downstream integrations.
"""
from __future__ import annotations

from typing import Any, Dict

import requests


class WebhookNotifier:
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def notify(self, payload: Dict[str, Any]) -> requests.Response:
        response = requests.post(self.webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        return response

