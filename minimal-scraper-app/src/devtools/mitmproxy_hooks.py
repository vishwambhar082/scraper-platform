# file: src/devtools/mitmproxy_hooks.py
"""
Skeleton for mitmproxy integration.

You can use this file as an add-on in mitmproxy to capture / replay traffic.
"""

from __future__ import annotations

from mitmproxy import http  # type: ignore[import]


def request(flow: http.HTTPFlow) -> None:  # pragma: no cover - external tooling
    """
    Called when a client request has been received.
    """
    # Add tagging / logging here if needed.
    return None
