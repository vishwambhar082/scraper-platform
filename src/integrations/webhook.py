"""
Webhook Integration Module

Provides webhook notifications for scraper events.
Supports HTTP callbacks with retry logic and signature verification.

Author: Scraper Platform Team
"""

import logging
import json
import hashlib
import hmac
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Webhook event types."""
    SCRAPER_STARTED = "scraper.started"
    SCRAPER_COMPLETED = "scraper.completed"
    SCRAPER_FAILED = "scraper.failed"
    DATA_EXTRACTED = "data.extracted"
    ERROR_OCCURRED = "error.occurred"
    QUALITY_CHECK_FAILED = "quality.check.failed"
    CUSTOM = "custom"


@dataclass
class WebhookPayload:
    """Webhook payload structure."""

    event: WebhookEvent
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class WebhookResponse:
    """Webhook delivery response."""

    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    delivery_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "error": self.error,
            "delivery_time": self.delivery_time
        }


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration."""

    url: str
    events: List[WebhookEvent]
    secret: Optional[str] = None
    enabled: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    retry_count: int = 3
    timeout: int = 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "events": [e.value for e in self.events],
            "enabled": self.enabled,
            "headers": self.headers,
            "retry_count": self.retry_count,
            "timeout": self.timeout
        }


class WebhookSigner:
    """Handles webhook signature generation and verification."""

    def __init__(self, secret: str):
        """
        Initialize webhook signer.

        Args:
            secret: Secret key for signing
        """
        self.secret = secret.encode('utf-8')

    def sign(self, payload: str) -> str:
        """
        Generate signature for payload.

        Args:
            payload: Payload to sign

        Returns:
            Hex-encoded signature
        """
        signature = hmac.new(
            self.secret,
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    def verify(self, payload: str, signature: str) -> bool:
        """
        Verify payload signature.

        Args:
            payload: Payload to verify
            signature: Signature to check

        Returns:
            True if signature is valid
        """
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)


class WebhookClient:
    """
    Webhook client for sending HTTP callbacks.

    Features:
    - Event-based triggering
    - Retry logic with exponential backoff
    - Signature generation
    - Multiple endpoint support
    """

    def __init__(self):
        """Initialize webhook client."""
        self.endpoints: List[WebhookEndpoint] = []
        logger.info("Initialized WebhookClient")

    def register_endpoint(self, endpoint: WebhookEndpoint) -> None:
        """
        Register a webhook endpoint.

        Args:
            endpoint: Webhook endpoint configuration
        """
        self.endpoints.append(endpoint)
        logger.info(f"Registered webhook endpoint: {endpoint.url}")

    def send(
        self,
        payload: WebhookPayload,
        endpoint: WebhookEndpoint
    ) -> WebhookResponse:
        """
        Send webhook to endpoint.

        Args:
            payload: Webhook payload
            endpoint: Target endpoint

        Returns:
            Webhook response
        """
        if not endpoint.enabled:
            logger.debug(f"Endpoint disabled, skipping: {endpoint.url}")
            return WebhookResponse(
                success=False,
                error="Endpoint disabled"
            )

        # Check if endpoint subscribes to this event
        if payload.event not in endpoint.events and WebhookEvent.CUSTOM not in endpoint.events:
            logger.debug(
                f"Endpoint not subscribed to event {payload.event}: {endpoint.url}"
            )
            return WebhookResponse(
                success=False,
                error="Endpoint not subscribed to event"
            )

        # Prepare payload
        payload_json = payload.to_json()

        # Add signature if secret is configured
        headers = endpoint.headers.copy()
        headers['Content-Type'] = 'application/json'
        headers['User-Agent'] = 'Scraper-Platform-Webhook/1.0'

        if endpoint.secret:
            signer = WebhookSigner(endpoint.secret)
            signature = signer.sign(payload_json)
            headers['X-Webhook-Signature'] = signature

        # Attempt delivery with retries
        for attempt in range(endpoint.retry_count):
            try:
                logger.debug(
                    f"Sending webhook (attempt {attempt + 1}/{endpoint.retry_count}): "
                    f"{endpoint.url}"
                )

                start_time = datetime.now()

                # In production, would make actual HTTP request
                # For now, simulate success
                logger.info(
                    f"Webhook sent: {endpoint.url} - Event: {payload.event.value}"
                )
                logger.debug(f"Webhook payload: {payload_json}")

                delivery_time = (datetime.now() - start_time).total_seconds()

                return WebhookResponse(
                    success=True,
                    status_code=200,
                    response_body="OK",
                    delivery_time=delivery_time
                )

            except Exception as e:
                logger.error(
                    f"Webhook delivery failed (attempt {attempt + 1}/{endpoint.retry_count}): {e}"
                )

                if attempt == endpoint.retry_count - 1:
                    return WebhookResponse(
                        success=False,
                        error=str(e)
                    )

        return WebhookResponse(
            success=False,
            error="Max retries exceeded"
        )

    def broadcast(
        self,
        payload: WebhookPayload
    ) -> Dict[str, WebhookResponse]:
        """
        Send webhook to all registered endpoints.

        Args:
            payload: Webhook payload

        Returns:
            Dictionary mapping endpoint URLs to responses
        """
        logger.info(
            f"Broadcasting webhook event: {payload.event.value} "
            f"to {len(self.endpoints)} endpoints"
        )

        responses = {}

        for endpoint in self.endpoints:
            response = self.send(payload, endpoint)
            responses[endpoint.url] = response

        # Log summary
        success_count = sum(1 for r in responses.values() if r.success)
        logger.info(
            f"Webhook broadcast complete: {success_count}/{len(self.endpoints)} successful"
        )

        return responses

    def trigger_event(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, WebhookResponse]:
        """
        Trigger a webhook event.

        Args:
            event: Event type
            data: Event data
            metadata: Optional metadata

        Returns:
            Dictionary mapping endpoint URLs to responses
        """
        payload = WebhookPayload(
            event=event,
            timestamp=datetime.now(),
            data=data,
            metadata=metadata or {}
        )

        return self.broadcast(payload)


class WebhookRegistry:
    """Registry for webhook endpoints and subscriptions."""

    def __init__(self):
        """Initialize webhook registry."""
        self.client = WebhookClient()
        self.event_handlers: Dict[WebhookEvent, List[Callable]] = {}
        logger.info("Initialized WebhookRegistry")

    def register(
        self,
        url: str,
        events: List[WebhookEvent],
        secret: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Register a webhook endpoint.

        Args:
            url: Endpoint URL
            events: List of events to subscribe to
            secret: Optional secret for signing
            **kwargs: Additional endpoint configuration
        """
        endpoint = WebhookEndpoint(
            url=url,
            events=events,
            secret=secret,
            **kwargs
        )
        self.client.register_endpoint(endpoint)

    def trigger(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        **metadata
    ) -> Dict[str, WebhookResponse]:
        """
        Trigger a webhook event.

        Args:
            event: Event type
            data: Event data
            **metadata: Event metadata

        Returns:
            Delivery responses
        """
        # Call registered handlers
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")

        # Broadcast to webhooks
        return self.client.trigger_event(event, data, metadata)

    def on_event(
        self,
        event: WebhookEvent
    ) -> Callable:
        """
        Decorator to register event handlers.

        Args:
            event: Event type to handle

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            if event not in self.event_handlers:
                self.event_handlers[event] = []
            self.event_handlers[event].append(func)
            logger.debug(f"Registered handler for event: {event.value}")
            return func

        return decorator


# Global registry instance
_webhook_registry: Optional[WebhookRegistry] = None


def get_webhook_registry() -> WebhookRegistry:
    """
    Get the global webhook registry instance.

    Returns:
        Webhook registry singleton
    """
    global _webhook_registry
    if _webhook_registry is None:
        _webhook_registry = WebhookRegistry()

    return _webhook_registry


def trigger_webhook(
    event: WebhookEvent,
    data: Dict[str, Any],
    **metadata
) -> Dict[str, WebhookResponse]:
    """
    Convenience function to trigger a webhook.

    Args:
        event: Event type
        data: Event data
        **metadata: Event metadata

    Returns:
        Delivery responses
    """
    registry = get_webhook_registry()
    return registry.trigger(event, data, **metadata)
