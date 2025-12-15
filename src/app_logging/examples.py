"""
Usage examples for structured logging system.

Run these examples to see structured logging in action.
"""

from pathlib import Path
from src.app_logging.structured_logger import (
    configure_structured_logging,
    get_structured_logger,
    setup_development_logging,
    setup_production_logging,
)
from src.app_logging.log_context import (
    bind_context,
    unbind_context,
    clear_context,
    log_context,
    with_context_from_kwargs,
    context_scope,
    nested_context,
    isolated_context,
    RunContext,
    StepContext,
    TaskContext,
)


# ============================================================================
# Example 1: Basic Logging
# ============================================================================

def example_basic_logging():
    """Basic structured logging example."""
    print("\n=== Example 1: Basic Logging ===\n")

    # Configure logging
    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        json_log_file="example_basic.jsonl",
        enable_console=True,
        enable_file=True,
    )

    # Get logger
    log = get_structured_logger(__name__)

    # Simple logs
    log.info("application_started", version="5.0")
    log.debug("debug_message", detail="This won't show at INFO level")
    log.warning("rate_limit_warning", requests_remaining=10)
    log.error("connection_error", host="example.com", port=443)

    # Structured event
    log.info(
        "scrape_completed",
        source="alfabeta",
        items_scraped=1250,
        duration_seconds=45.3,
        success=True,
    )

    print("Check logs/examples/example_basic.jsonl for output")


# ============================================================================
# Example 2: Context Binding
# ============================================================================

def example_context_binding():
    """Context binding example."""
    print("\n=== Example 2: Context Binding ===\n")

    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        json_log_file="example_context.jsonl",
        enable_console=True,
    )

    log = get_structured_logger(__name__)

    # Bind context
    bind_context(run_id="12345", source="alfabeta")

    log.info("step_1_started")  # Includes run_id and source
    log.info("step_1_completed")  # Also includes run_id and source

    # Add more context
    bind_context(step_id="step_2")

    log.info("step_2_started")  # Includes run_id, source, AND step_id

    # Unbind specific context
    unbind_context("step_id")

    log.info("step_3_started")  # Only run_id and source

    # Clear all context
    clear_context()

    log.info("final_log")  # No context

    print("Check logs/examples/example_context.jsonl for output")


# ============================================================================
# Example 3: Context Decorators
# ============================================================================

def example_decorators():
    """Context decorator examples."""
    print("\n=== Example 3: Context Decorators ===\n")

    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        json_log_file="example_decorators.jsonl",
        enable_console=True,
    )

    log = get_structured_logger(__name__)

    @log_context(source="alfabeta", job_id="daily_scrape")
    def scrape_job():
        log.info("job_started")
        fetch_data()
        parse_data()
        log.info("job_completed")

    def fetch_data():
        log.info("fetching_data")

    def parse_data():
        log.info("parsing_data")

    @with_context_from_kwargs("run_id", "source")
    def process_run(run_id: str, source: str, data: dict):
        log.info("processing_started", data_size=len(data))
        log.info("processing_completed")

    # Execute decorated functions
    scrape_job()
    process_run(run_id="12345", source="alfabeta", data={"key": "value"})

    print("Check logs/examples/example_decorators.jsonl for output")


# ============================================================================
# Example 4: Context Managers
# ============================================================================

def example_context_managers():
    """Context manager examples."""
    print("\n=== Example 4: Context Managers ===\n")

    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        json_log_file="example_context_managers.jsonl",
        enable_console=True,
    )

    log = get_structured_logger(__name__)

    # Scoped context
    with context_scope(run_id="12345", source="alfabeta"):
        log.info("inside_scope")

    log.info("outside_scope")  # No context

    # Nested context
    bind_context(run_id="12345")

    with nested_context(step_id="step_1"):
        log.info("step_1")

    with nested_context(step_id="step_2"):
        log.info("step_2")

    # Isolated context
    with isolated_context(task_id="background_task"):
        log.info("isolated_task")

    log.info("back_to_parent")

    clear_context()

    print("Check logs/examples/example_context_managers.jsonl for output")


# ============================================================================
# Example 5: Specialized Context Managers
# ============================================================================

def example_specialized_contexts():
    """Specialized context manager examples."""
    print("\n=== Example 5: Specialized Context Managers ===\n")

    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        json_log_file="example_specialized.jsonl",
        enable_console=True,
    )

    log = get_structured_logger(__name__)

    # Run context
    with RunContext(run_id="12345", source="alfabeta", environment="production"):
        log.info("run_started")

        # Nested step contexts
        with StepContext(step_id="fetch", step_type="FETCH", step_index=0):
            log.info("step_started")
            log.info("fetching_pages", pages=100)
            log.info("step_completed")

        with StepContext(step_id="parse", step_type="PARSE", step_index=1):
            log.info("step_started")
            log.info("parsing_items", items=1250)
            log.info("step_completed")

        with StepContext(step_id="export", step_type="EXPORT", step_index=2):
            log.info("step_started")
            log.info("exporting_data", format="json")
            log.info("step_completed")

        log.info("run_completed")

    # Task context
    with TaskContext(task_id="daily_scrape", task_type="scraping"):
        log.info("task_started")
        log.info("task_completed")

    print("Check logs/examples/example_specialized.jsonl for output")


# ============================================================================
# Example 6: Exception Logging
# ============================================================================

def example_exception_logging():
    """Exception logging example."""
    print("\n=== Example 6: Exception Logging ===\n")

    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        json_log_file="example_exceptions.jsonl",
        enable_console=True,
    )

    log = get_structured_logger(__name__)

    # Exception with automatic traceback
    try:
        pass
    except ZeroDivisionError:
        log.exception(
            "division_error",
            operation="divide",
            numerator=1,
            denominator=0,
        )

    # Nested exception
    try:
        try:
            raise ValueError("Inner error")
        except ValueError:
            raise RuntimeError("Outer error") from None
    except RuntimeError:
        log.exception("nested_error", context="example")

    print("Check logs/examples/example_exceptions.jsonl for output")


# ============================================================================
# Example 7: Sensitive Data Masking
# ============================================================================

def example_sensitive_data_masking():
    """Sensitive data masking example."""
    print("\n=== Example 7: Sensitive Data Masking ===\n")

    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        json_log_file="example_masking.jsonl",
        enable_console=True,
    )

    log = get_structured_logger(__name__)

    # Passwords and tokens are automatically masked
    log.info(
        "authentication",
        username="user123",
        password="secret123",  # Masked
        api_key="sk-1234567890",  # Masked
    )

    # URLs with credentials
    log.info(
        "proxy_configured",
        proxy_url="http://user:pass@proxy.com:8080",  # Credentials masked
    )

    # Bearer tokens
    log.info(
        "api_request",
        url="https://api.example.com/data",
        authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",  # Masked
    )

    # Cookie values
    log.info(
        "session_created",
        user_id="user123",
        session_cookie="session=abc123xyz789; path=/; httponly",  # Masked
    )

    print("Check logs/examples/example_masking.jsonl for masked output")


# ============================================================================
# Example 8: Complete Scraper Example
# ============================================================================

class ExampleScraper:
    """Example scraper using structured logging."""

    def __init__(self):
        self.log = get_structured_logger(self.__class__.__name__)

    def scrape(self, run_id: str, source: str):
        """Run a complete scrape with structured logging."""
        with RunContext(run_id=run_id, source=source, environment="development"):
            self.log.info("scrape_started", max_pages=100, parallel=True)

            try:
                # Fetch
                pages = self._fetch_pages()
                # Parse
                items = self._parse_pages(pages)
                # Validate
                valid_items = self._validate_items(items)
                # Export
                self._export_items(valid_items)

                self.log.info(
                    "scrape_completed",
                    pages_fetched=len(pages),
                    items_extracted=len(items),
                    items_valid=len(valid_items),
                    success_rate=len(valid_items) / len(items) if items else 0,
                )

            except Exception as e:
                self.log.exception("scrape_failed", error=str(e))
                raise

    def _fetch_pages(self):
        """Fetch pages."""
        with StepContext(step_id="fetch", step_type="FETCH", step_index=0):
            self.log.info("step_started")

            # Simulate fetching
            pages = ["page1", "page2", "page3"]

            self.log.info("step_completed", pages_fetched=len(pages))
            return pages

    def _parse_pages(self, pages):
        """Parse pages."""
        with StepContext(step_id="parse", step_type="PARSE", step_index=1):
            self.log.info("step_started", pages_to_parse=len(pages))

            # Simulate parsing
            items = [{"id": i, "title": f"Item {i}"} for i in range(100)]

            self.log.info("step_completed", items_extracted=len(items))
            return items

    def _validate_items(self, items):
        """Validate items."""
        with StepContext(step_id="validate", step_type="VALIDATE", step_index=2):
            self.log.info("step_started", items_to_validate=len(items))

            # Simulate validation
            valid_items = [item for item in items if item["id"] % 10 != 0]

            self.log.info(
                "step_completed",
                items_valid=len(valid_items),
                items_invalid=len(items) - len(valid_items),
            )
            return valid_items

    def _export_items(self, items):
        """Export items."""
        with StepContext(step_id="export", step_type="EXPORT", step_index=3):
            self.log.info("step_started", items_to_export=len(items))

            # Simulate export
            output_file = "output/items.json"

            self.log.info("step_completed", output_file=output_file)


def example_complete_scraper():
    """Complete scraper example."""
    print("\n=== Example 8: Complete Scraper ===\n")

    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        json_log_file="example_scraper.jsonl",
        enable_console=True,
    )

    scraper = ExampleScraper()
    scraper.scrape(run_id="12345", source="alfabeta")

    print("Check logs/examples/example_scraper.jsonl for output")


# ============================================================================
# Example 9: Production Setup
# ============================================================================

def example_production_setup():
    """Production logging setup example."""
    print("\n=== Example 9: Production Setup ===\n")

    # Production: Optimized for performance
    setup_production_logging(
        log_level="INFO",
        log_dir=Path("logs/examples"),
        enable_console=False,  # Only file output
    )

    log = get_structured_logger(__name__)

    log.info(
        "production_example",
        environment="production",
        optimized=True,
        caller_info=False,
    )

    print("Check logs/examples/scraper_structured.jsonl for output")


# ============================================================================
# Example 10: Development Setup
# ============================================================================

def example_development_setup():
    """Development logging setup example."""
    print("\n=== Example 10: Development Setup ===\n")

    # Development: Verbose with caller info
    setup_development_logging(
        log_level="DEBUG",
        log_dir=Path("logs/examples"),
    )

    log = get_structured_logger(__name__)

    log.debug(
        "development_example",
        environment="development",
        verbose=True,
        caller_info=True,
    )

    print("Check logs/examples/scraper_structured.jsonl for output")


# ============================================================================
# Main: Run All Examples
# ============================================================================

def run_all_examples():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("STRUCTURED LOGGING EXAMPLES")
    print("=" * 60)

    # Create log directory
    Path("logs/examples").mkdir(parents=True, exist_ok=True)

    # Run examples
    example_basic_logging()
    example_context_binding()
    example_decorators()
    example_context_managers()
    example_specialized_contexts()
    example_exception_logging()
    example_sensitive_data_masking()
    example_complete_scraper()
    example_production_setup()
    example_development_setup()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("Check logs/examples/ for output files")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_examples()
