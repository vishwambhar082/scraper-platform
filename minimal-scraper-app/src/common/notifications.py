"""
Lightweight notification dispatcher (Slack/email stubs).
"""
from __future__ import annotations

from typing import Dict

from src.common.logging_utils import get_logger

log = get_logger("notifications")


class Notifier:
    def __init__(self, channel: str) -> None:
        self.channel = channel

    def send(self, message: str, metadata: Dict[str, object] | None = None) -> None:
        log.info(
            "notification",
            extra={"channel": self.channel, "message": message, "metadata": metadata or {}},
        )

