"""
Basic tests for structured logging functionality.

Run with: python -m pytest src/app_logging/test_structured_logging.py -v
"""

import json
import tempfile
from pathlib import Path

import pytest


def test_basic_logging():
    """Test basic structured logging."""
    from src.app_logging.structured_logger import (
        configure_structured_logging,
        get_structured_logger,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_file = "test.jsonl"

        configure_structured_logging(
            log_level="INFO",
            log_dir=log_dir,
            json_log_file=log_file,
            enable_console=False,
            enable_file=True,
        )

        log = get_structured_logger(__name__)
        log.info("test_message", test_field="test_value")

        # Read log file
        log_path = log_dir / log_file
        assert log_path.exists()

        with open(log_path) as f:
            lines = f.readlines()
            assert len(lines) >= 1

            # Parse first log entry
            log_entry = json.loads(lines[0])
            assert log_entry["event"] == "test_message"
            assert log_entry["level"] == "INFO"
            assert log_entry["test_field"] == "test_value"
            assert "timestamp" in log_entry


def test_context_binding():
    """Test context binding functionality."""
    from src.app_logging.structured_logger import (
        configure_structured_logging,
        get_structured_logger,
    )
    from src.app_logging.log_context import bind_context, clear_context, get_context

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_file = "test_context.jsonl"

        configure_structured_logging(
            log_level="INFO",
            log_dir=log_dir,
            json_log_file=log_file,
            enable_console=False,
            enable_file=True,
        )

        log = get_structured_logger(__name__)

        # Bind context
        bind_context(run_id="12345", source="test")

        # Verify context
        context = get_context()
        assert context["run_id"] == "12345"
        assert context["source"] == "test"

        # Log with context
        log.info("test_with_context")

        # Read log file
        log_path = log_dir / log_file
        with open(log_path) as f:
            lines = f.readlines()
            log_entry = json.loads(lines[0])
            assert log_entry["run_id"] == "12345"
            assert log_entry["source"] == "test"

        # Clear context
        clear_context()
        context = get_context()
        assert len(context) == 0


def test_context_manager():
    """Test context manager functionality."""
    from src.app_logging.structured_logger import (
        configure_structured_logging,
        get_structured_logger,
    )
    from src.app_logging.log_context import RunContext

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_file = "test_context_manager.jsonl"

        configure_structured_logging(
            log_level="INFO",
            log_dir=log_dir,
            json_log_file=log_file,
            enable_console=False,
            enable_file=True,
        )

        log = get_structured_logger(__name__)

        # Use context manager
        with RunContext(run_id="67890", source="alfabeta"):
            log.info("inside_context")

        log.info("outside_context")

        # Read log file
        log_path = log_dir / log_file
        with open(log_path) as f:
            lines = f.readlines()

            # Inside context
            log_entry1 = json.loads(lines[0])
            assert log_entry1["run_id"] == "67890"
            assert log_entry1["source"] == "alfabeta"

            # Outside context
            log_entry2 = json.loads(lines[1])
            assert "run_id" not in log_entry2
            assert "source" not in log_entry2


def test_sensitive_data_masking():
    """Test sensitive data masking."""
    from src.app_logging.structured_logger import (
        configure_structured_logging,
        get_structured_logger,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_file = "test_masking.jsonl"

        configure_structured_logging(
            log_level="INFO",
            log_dir=log_dir,
            json_log_file=log_file,
            enable_console=False,
            enable_file=True,
        )

        log = get_structured_logger(__name__)

        # Log with sensitive data
        log.info(
            "authentication",
            username="testuser",
            password="secret123",
            api_key="sk-1234567890",
        )

        # Read log file
        log_path = log_dir / log_file
        with open(log_path) as f:
            lines = f.readlines()
            log_entry = json.loads(lines[0])

            # Check masking
            assert log_entry["username"] == "testuser"
            assert log_entry["password"] == "***REDACTED***"
            assert log_entry["api_key"] == "***REDACTED***"


def test_exception_logging():
    """Test exception logging with traceback."""
    from src.app_logging.structured_logger import (
        configure_structured_logging,
        get_structured_logger,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_file = "test_exception.jsonl"

        configure_structured_logging(
            log_level="INFO",
            log_dir=log_dir,
            json_log_file=log_file,
            enable_console=False,
            enable_file=True,
        )

        log = get_structured_logger(__name__)

        # Log exception
        try:
            result = 1 / 0
        except ZeroDivisionError:
            log.exception("division_error", numerator=1, denominator=0)

        # Read log file
        log_path = log_dir / log_file
        with open(log_path) as f:
            lines = f.readlines()
            log_entry = json.loads(lines[0])

            # Check exception info
            assert "exception" in log_entry
            assert log_entry["exception"]["type"] == "ZeroDivisionError"
            assert "traceback" in log_entry["exception"]
            assert log_entry["numerator"] == 1
            assert log_entry["denominator"] == 0


def test_decorator():
    """Test log_context decorator."""
    from src.app_logging.structured_logger import (
        configure_structured_logging,
        get_structured_logger,
    )
    from src.app_logging.log_context import log_context

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_file = "test_decorator.jsonl"

        configure_structured_logging(
            log_level="INFO",
            log_dir=log_dir,
            json_log_file=log_file,
            enable_console=False,
            enable_file=True,
        )

        log = get_structured_logger(__name__)

        @log_context(job_id="test_job", source="test_source")
        def test_function():
            log.info("inside_function")

        test_function()

        # Read log file
        log_path = log_dir / log_file
        with open(log_path) as f:
            lines = f.readlines()
            log_entry = json.loads(lines[0])

            # Check context from decorator
            assert log_entry["job_id"] == "test_job"
            assert log_entry["source"] == "test_source"


def test_nested_context():
    """Test nested context management."""
    from src.app_logging.structured_logger import (
        configure_structured_logging,
        get_structured_logger,
    )
    from src.app_logging.log_context import bind_context, nested_context, clear_context

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        log_file = "test_nested.jsonl"

        configure_structured_logging(
            log_level="INFO",
            log_dir=log_dir,
            json_log_file=log_file,
            enable_console=False,
            enable_file=True,
        )

        log = get_structured_logger(__name__)

        # Bind base context
        bind_context(run_id="12345")

        # Nested context
        with nested_context(step_id="step_1"):
            log.info("nested_log")

        log.info("after_nested")

        # Read log file
        log_path = log_dir / log_file
        with open(log_path) as f:
            lines = f.readlines()

            # Inside nested context
            log_entry1 = json.loads(lines[0])
            assert log_entry1["run_id"] == "12345"
            assert log_entry1["step_id"] == "step_1"

            # After nested context
            log_entry2 = json.loads(lines[1])
            assert log_entry2["run_id"] == "12345"
            assert "step_id" not in log_entry2

        clear_context()


def test_production_setup():
    """Test production logging setup."""
    from src.app_logging.structured_logger import setup_production_logging

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        setup_production_logging(log_level="INFO", log_dir=log_dir, enable_console=False)

        # Verify log file is created
        log_file = log_dir / "scraper_structured.jsonl"

        from src.app_logging.structured_logger import get_structured_logger
        log = get_structured_logger(__name__)
        log.info("production_test")

        assert log_file.exists()


def test_development_setup():
    """Test development logging setup."""
    from src.app_logging.structured_logger import setup_development_logging

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        setup_development_logging(log_level="DEBUG", log_dir=log_dir)

        # Verify log file is created
        log_file = log_dir / "scraper_structured.jsonl"

        from src.app_logging.structured_logger import get_structured_logger
        log = get_structured_logger(__name__)
        log.debug("development_test")

        assert log_file.exists()


if __name__ == "__main__":
    # Run tests manually
    print("Running structured logging tests...\n")

    test_basic_logging()
    print("✓ Basic logging test passed")

    test_context_binding()
    print("✓ Context binding test passed")

    test_context_manager()
    print("✓ Context manager test passed")

    test_sensitive_data_masking()
    print("✓ Sensitive data masking test passed")

    test_exception_logging()
    print("✓ Exception logging test passed")

    test_decorator()
    print("✓ Decorator test passed")

    test_nested_context()
    print("✓ Nested context test passed")

    test_production_setup()
    print("✓ Production setup test passed")

    test_development_setup()
    print("✓ Development setup test passed")

    print("\n✅ All tests passed!")
