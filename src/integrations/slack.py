"""
Slack Integration Module

Provides Slack notifications for scraper events and alerts.
Supports rich messages, threading, and interactive components.

Author: Scraper Platform Team
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SlackMessage:
    """Slack message structure."""

    text: str
    channel: Optional[str] = None
    username: Optional[str] = "Scraper Bot"
    icon_emoji: Optional[str] = ":robot_face:"
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    thread_ts: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Slack API format."""
        payload = {
            "text": self.text,
            "username": self.username,
            "icon_emoji": self.icon_emoji
        }

        if self.channel:
            payload["channel"] = self.channel

        if self.blocks:
            payload["blocks"] = self.blocks

        if self.attachments:
            payload["attachments"] = self.attachments

        if self.thread_ts:
            payload["thread_ts"] = self.thread_ts

        return payload


class SlackMessageBuilder:
    """Builder for complex Slack messages."""

    def __init__(self, text: str):
        """
        Initialize message builder.

        Args:
            text: Main message text
        """
        self.message = SlackMessage(text=text)

    def add_header(self, text: str) -> 'SlackMessageBuilder':
        """Add header block."""
        self.message.blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": text
            }
        })
        return self

    def add_section(self, text: str, markdown: bool = True) -> 'SlackMessageBuilder':
        """Add section block."""
        self.message.blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn" if markdown else "plain_text",
                "text": text
            }
        })
        return self

    def add_fields(self, fields: Dict[str, str]) -> 'SlackMessageBuilder':
        """Add fields to message."""
        field_blocks = [
            {
                "type": "mrkdwn",
                "text": f"*{key}*\n{value}"
            }
            for key, value in fields.items()
        ]

        self.message.blocks.append({
            "type": "section",
            "fields": field_blocks
        })
        return self

    def add_divider(self) -> 'SlackMessageBuilder':
        """Add divider."""
        self.message.blocks.append({"type": "divider"})
        return self

    def add_attachment(
        self,
        text: str,
        color: str = "good",
        fields: Optional[List[Dict[str, str]]] = None
    ) -> 'SlackMessageBuilder':
        """Add attachment."""
        attachment = {
            "text": text,
            "color": color
        }

        if fields:
            attachment["fields"] = fields

        self.message.attachments.append(attachment)
        return self

    def set_channel(self, channel: str) -> 'SlackMessageBuilder':
        """Set channel."""
        self.message.channel = channel
        return self

    def set_thread(self, thread_ts: str) -> 'SlackMessageBuilder':
        """Set thread timestamp."""
        self.message.thread_ts = thread_ts
        return self

    def build(self) -> SlackMessage:
        """Build the message."""
        return self.message


class SlackClient:
    """
    Slack API client for sending notifications.

    Features:
    - Message formatting
    - Rich blocks and attachments
    - Thread support
    - Error handling
    """

    def __init__(self, webhook_url: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize Slack client.

        Args:
            webhook_url: Incoming webhook URL
            token: Bot token (alternative to webhook)
        """
        self.webhook_url = webhook_url
        self.token = token
        self.default_channel: Optional[str] = None
        logger.info("Initialized SlackClient")

    def send_message(
        self,
        message: SlackMessage,
        raise_on_error: bool = False
    ) -> bool:
        """
        Send a message to Slack.

        Args:
            message: Message to send
            raise_on_error: Whether to raise exception on error

        Returns:
            True if sent successfully
        """
        try:
            # Use default channel if not specified
            if not message.channel and self.default_channel:
                message.channel = self.default_channel

            payload = message.to_dict()
            logger.debug(f"Sending Slack message: {message.text[:50]}...")

            # In production, would make actual HTTP request
            # For now, just log
            logger.info(f"Slack message: {json.dumps(payload, indent=2)}")

            return True

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            if raise_on_error:
                raise
            return False

    def send_simple(
        self,
        text: str,
        channel: Optional[str] = None,
        emoji: str = ":robot_face:"
    ) -> bool:
        """
        Send a simple text message.

        Args:
            text: Message text
            channel: Channel to send to
            emoji: Icon emoji

        Returns:
            True if sent successfully
        """
        message = SlackMessage(
            text=text,
            channel=channel,
            icon_emoji=emoji
        )
        return self.send_message(message)

    def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "warning",
        details: Optional[Dict[str, str]] = None,
        channel: Optional[str] = None
    ) -> bool:
        """
        Send an alert message.

        Args:
            title: Alert title
            message: Alert message
            severity: Severity level (info, warning, error, critical)
            details: Additional details
            channel: Channel to send to

        Returns:
            True if sent successfully
        """
        # Map severity to color
        color_map = {
            "info": "#36a64f",
            "warning": "#ff9900",
            "error": "#ff0000",
            "critical": "#8b0000"
        }

        color = color_map.get(severity, "#808080")
        emoji_map = {
            "info": ":information_source:",
            "warning": ":warning:",
            "error": ":x:",
            "critical": ":rotating_light:"
        }

        emoji = emoji_map.get(severity, ":bell:")

        builder = SlackMessageBuilder(text=title)
        builder.add_header(f"{emoji} {title}")
        builder.add_section(message)

        if details:
            builder.add_divider()
            builder.add_fields(details)

        if channel:
            builder.set_channel(channel)

        # Add colored attachment for severity
        builder.add_attachment(
            text=f"Severity: {severity.upper()}",
            color=color
        )

        return self.send_message(builder.build())

    def send_scraper_status(
        self,
        scraper_name: str,
        status: str,
        metrics: Optional[Dict[str, Any]] = None,
        channel: Optional[str] = None
    ) -> bool:
        """
        Send scraper status update.

        Args:
            scraper_name: Name of scraper
            status: Status (started, completed, failed)
            metrics: Execution metrics
            channel: Channel to send to

        Returns:
            True if sent successfully
        """
        status_emoji = {
            "started": ":arrow_forward:",
            "completed": ":white_check_mark:",
            "failed": ":x:",
            "running": ":hourglass:"
        }

        emoji = status_emoji.get(status.lower(), ":information_source:")
        title = f"{emoji} Scraper {status}: {scraper_name}"

        builder = SlackMessageBuilder(text=title)
        builder.add_header(title)

        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        builder.add_section(f"*Time:* {timestamp}")

        if metrics:
            builder.add_divider()
            builder.add_fields({
                k: str(v) for k, v in metrics.items()
            })

        if channel:
            builder.set_channel(channel)

        return self.send_message(builder.build())

    def send_error_report(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, str]] = None,
        channel: Optional[str] = None
    ) -> bool:
        """
        Send error report.

        Args:
            error_type: Type of error
            error_message: Error message
            context: Error context
            channel: Channel to send to

        Returns:
            True if sent successfully
        """
        return self.send_alert(
            title=f"Error: {error_type}",
            message=f"```{error_message}```",
            severity="error",
            details=context,
            channel=channel
        )


# Global client instance
_slack_client: Optional[SlackClient] = None


def get_slack_client() -> SlackClient:
    """
    Get the global Slack client instance.

    Returns:
        Slack client singleton
    """
    global _slack_client
    if _slack_client is None:
        import os
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        token = os.getenv("SLACK_BOT_TOKEN")
        _slack_client = SlackClient(webhook_url=webhook_url, token=token)

    return _slack_client


def send_slack_message(text: str, channel: Optional[str] = None) -> bool:
    """
    Convenience function to send a Slack message.

    Args:
        text: Message text
        channel: Optional channel

    Returns:
        True if sent successfully
    """
    client = get_slack_client()
    return client.send_simple(text, channel)


def send_slack_alert(
    title: str,
    message: str,
    severity: str = "warning",
    **kwargs
) -> bool:
    """
    Convenience function to send a Slack alert.

    Args:
        title: Alert title
        message: Alert message
        severity: Severity level
        **kwargs: Additional arguments

    Returns:
        True if sent successfully
    """
    client = get_slack_client()
    return client.send_alert(title, message, severity, **kwargs)
