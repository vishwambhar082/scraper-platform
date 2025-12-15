"""
LLM Token and Cost Tracking

Track token usage and costs across LLM providers using tiktoken.
Provides per-run, per-model, and aggregate cost analytics.

Author: Scraper Platform Team
Date: 2025-12-13
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.common.logging_utils import get_logger

log = get_logger("llm_cost_tracker")


# Pricing per 1M tokens (as of December 2025)
MODEL_PRICING = {
    # OpenAI
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic Claude
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-coder": {"input": 0.14, "output": 0.28},
    # Groq
    "llama-3-70b": {"input": 0.59, "output": 0.79},
    "mixtral-8x7b": {"input": 0.27, "output": 0.27},
}


@dataclass
class TokenUsage:
    """Token usage for a single LLM call."""

    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime = field(default_factory=datetime.now)
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    prompt_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp.isoformat(),
            "run_id": self.run_id,
            "step_id": self.step_id,
            "prompt_name": self.prompt_name,
            "metadata": self.metadata,
        }


@dataclass
class CostSummary:
    """Summary of token usage and costs."""

    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    by_model: Dict[str, Dict[str, Any]]
    by_run: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "by_model": self.by_model,
            "by_run": self.by_run,
        }


class LLMCostTracker:
    """
    Track LLM token usage and costs.

    Features:
    - Automatic token counting using tiktoken
    - Per-model cost calculation
    - SQLite storage for persistence
    - Aggregate cost analytics
    - Per-run cost tracking
    - Export to JSON/CSV
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize LLM cost tracker.

        Args:
            db_path: Path to SQLite database (default: ./data/llm_costs.db)
        """
        self.db_path = Path(db_path or "./data/llm_costs.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._tiktoken_cache: Dict[str, Any] = {}

        self._init_db()

        log.info(f"Initialized LLM cost tracker: {self.db_path}")

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    run_id TEXT,
                    step_id TEXT,
                    prompt_name TEXT,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_model ON llm_usage(model)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_run_id ON llm_usage(run_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON llm_usage(timestamp)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get thread-safe database connection."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for
            model: Model name for encoding

        Returns:
            Number of tokens
        """
        try:
            import tiktoken

            # Get or create encoder
            if model not in self._tiktoken_cache:
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    # Fallback to cl100k_base for unknown models
                    encoding = tiktoken.get_encoding("cl100k_base")
                self._tiktoken_cache[model] = encoding

            encoding = self._tiktoken_cache[model]
            return len(encoding.encode(text))

        except ImportError:
            # Fallback to rough estimation if tiktoken not installed
            log.warning("tiktoken not installed, using rough token estimation")
            return len(text.split()) * 1.3  # Rough approximation

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost for token usage.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        # Normalize model name
        model_key = model.lower()

        # Find matching pricing
        pricing = None
        for key, value in MODEL_PRICING.items():
            if key in model_key:
                pricing = value
                break

        if not pricing:
            log.warning(f"No pricing found for model {model}, using default")
            pricing = {"input": 1.0, "output": 2.0}  # Default fallback

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def track(
        self,
        model: str,
        prompt: str,
        response: str,
        run_id: Optional[str] = None,
        step_id: Optional[str] = None,
        prompt_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TokenUsage:
        """Track LLM usage.

        Args:
            model: Model name
            prompt: Input prompt text
            response: Output response text
            run_id: Optional run identifier
            step_id: Optional step identifier
            prompt_name: Optional prompt template name
            metadata: Optional metadata

        Returns:
            TokenUsage record
        """
        # Count tokens
        input_tokens = self.count_tokens(prompt, model)
        output_tokens = self.count_tokens(response, model)
        total_tokens = input_tokens + output_tokens

        # Calculate cost
        cost_usd = self.calculate_cost(model, input_tokens, output_tokens)

        # Create usage record
        usage = TokenUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            run_id=run_id,
            step_id=step_id,
            prompt_name=prompt_name,
            metadata=metadata or {},
        )

        # Save to database
        self._save_usage(usage)

        log.debug(
            f"Tracked LLM usage: {model} - {total_tokens} tokens (${cost_usd:.4f})"
        )

        return usage

    def _save_usage(self, usage: TokenUsage) -> None:
        """Save usage record to database.

        Args:
            usage: TokenUsage record
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO llm_usage
                (model, input_tokens, output_tokens, total_tokens, cost_usd,
                 timestamp, run_id, step_id, prompt_name, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usage.model,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.total_tokens,
                    usage.cost_usd,
                    usage.timestamp.isoformat(),
                    usage.run_id,
                    usage.step_id,
                    usage.prompt_name,
                    json.dumps(usage.metadata),
                ),
            )
            conn.commit()

    def get_summary(
        self,
        run_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CostSummary:
        """Get cost summary.

        Args:
            run_id: Optional filter by run_id
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            CostSummary
        """
        with self._get_connection() as conn:
            # Build query
            query = "SELECT * FROM llm_usage WHERE 1=1"
            params = []

            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            rows = conn.execute(query, params).fetchall()

        # Calculate summary
        total_requests = len(rows)
        total_input_tokens = sum(r["input_tokens"] for r in rows)
        total_output_tokens = sum(r["output_tokens"] for r in rows)
        total_tokens = sum(r["total_tokens"] for r in rows)
        total_cost_usd = sum(r["cost_usd"] for r in rows)

        # Group by model
        by_model: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            model = row["model"]
            if model not in by_model:
                by_model[model] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }

            by_model[model]["requests"] += 1
            by_model[model]["input_tokens"] += row["input_tokens"]
            by_model[model]["output_tokens"] += row["output_tokens"]
            by_model[model]["total_tokens"] += row["total_tokens"]
            by_model[model]["cost_usd"] += row["cost_usd"]

        # Group by run
        by_run: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            rid = row["run_id"] or "unknown"
            if rid not in by_run:
                by_run[rid] = {
                    "requests": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }

            by_run[rid]["requests"] += 1
            by_run[rid]["total_tokens"] += row["total_tokens"]
            by_run[rid]["cost_usd"] += row["cost_usd"]

        return CostSummary(
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_tokens,
            total_cost_usd=total_cost_usd,
            by_model=by_model,
            by_run=by_run,
        )

    def export_to_json(self, output_path: str) -> None:
        """Export usage data to JSON.

        Args:
            output_path: Output file path
        """
        summary = self.get_summary()

        with open(output_path, "w") as f:
            json.dump(summary.to_dict(), f, indent=2)

        log.info(f"Exported LLM usage to {output_path}")


# Global cost tracker singleton
_cost_tracker: Optional[LLMCostTracker] = None


def get_cost_tracker(db_path: Optional[str] = None) -> LLMCostTracker:
    """Get global LLM cost tracker.

    Args:
        db_path: Optional database path (only used on first call)

    Returns:
        LLMCostTracker instance
    """
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = LLMCostTracker(db_path)
    return _cost_tracker
