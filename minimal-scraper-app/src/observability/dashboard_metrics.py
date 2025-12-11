# file: src/observability/dashboard_metrics.py
"""
Helper functions to aggregate metrics for the frontend dashboard.
"""

from __future__ import annotations

from typing import Any, Dict, List


def summarize_runs(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Produce a simple summary payload (counts by status, etc.)
    that the React dashboard can consume directly.
    """
    summary = {"total": len(rows), "by_status": {}}
    for row in rows:
        status = row.get("status", "unknown")
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
    return summary
