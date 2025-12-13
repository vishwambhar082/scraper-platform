# Structured Logging - Quick Start

Get started with structured JSON logging in 5 minutes.

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Import and configure:
   ```python
   from src.app_logging import configure_structured_logging, get_structured_logger

   # Configure once at startup
   configure_structured_logging(
       log_level="INFO",
       enable_console=True,
       enable_file=True,
   )

   # Get a logger
   log = get_structured_logger(__name__)
   ```

## Basic Usage

### Simple Logging

```python
from src.app_logging import get_structured_logger

log = get_structured_logger(__name__)

log.info("user_login", user_id=123, username="alice")
log.error("connection_failed", host="api.example.com", retry_count=3)
```

**Output:**
```json
{"timestamp":"2025-12-13T19:45:23.123456Z","level":"INFO","logger":"my_module","event":"user_login","user_id":123,"username":"alice"}
{"timestamp":"2025-12-13T19:45:24.234567Z","level":"ERROR","logger":"my_module","event":"connection_failed","host":"api.example.com","retry_count":3}
```

### With Context

```python
from src.app_logging import get_structured_logger, RunContext

log = get_structured_logger(__name__)

# Context is automatically included in all logs
with RunContext(run_id="12345", source="alfabeta"):
    log.info("scrape_started")
    log.info("scrape_completed", items=1250)
```

**Output:**
```json
{"timestamp":"2025-12-13T19:45:25.345678Z","level":"INFO","logger":"my_module","event":"scrape_started","run_id":"12345","source":"alfabeta"}
{"timestamp":"2025-12-13T19:45:26.456789Z","level":"INFO","logger":"my_module","event":"scrape_completed","run_id":"12345","source":"alfabeta","items":1250}
```

## Common Patterns

### Pattern 1: Scraper with Context

```python
from src.app_logging import get_structured_logger, RunContext, StepContext

log = get_structured_logger(__name__)

def scrape_alfabeta(run_id: str):
    with RunContext(run_id=run_id, source="alfabeta"):
        log.info("scrape_started")

        with StepContext(step_id="fetch", step_type="FETCH"):
            log.info("fetching_pages", max_pages=100)
            # ... fetch logic ...
            log.info("fetch_completed", pages=95)

        with StepContext(step_id="parse", step_type="PARSE"):
            log.info("parsing_data")
            # ... parse logic ...
            log.info("parse_completed", items=1250)

        log.info("scrape_completed")
```

### Pattern 2: Decorator-Based Context

```python
from src.app_logging import get_structured_logger, log_context

log = get_structured_logger(__name__)

@log_context(job_id="daily_scrape", source="alfabeta")
def daily_scrape():
    log.info("job_started")
    # All logs automatically include job_id and source
    process_data()
    log.info("job_completed")

def process_data():
    log.info("processing")  # Still includes context from decorator
```

### Pattern 3: Exception Logging

```python
from src.app_logging import get_structured_logger

log = get_structured_logger(__name__)

try:
    result = risky_operation()
except Exception:
    log.exception("operation_failed", operation="risky_operation")
    # Automatically includes exception type, message, and full traceback
```

## Environment-Specific Setup

### Development

```python
from src.app_logging import setup_development_logging

setup_development_logging(log_level="DEBUG")
```

- Verbose output
- Caller information included
- Console + file output

### Production

```python
from src.app_logging import setup_production_logging

setup_production_logging(log_level="INFO")
```

- Optimized for performance
- No caller information
- File output with rotation

## Next Steps

- Read the [Complete Guide](STRUCTURED_LOGGING_GUIDE.md) for advanced features
- Check out [examples.py](examples.py) for runnable code examples
- Review [Migration Guide](STRUCTURED_LOGGING_GUIDE.md#migration-guide) to migrate existing code

## Key Benefits

1. **Machine-Readable**: JSON format for easy parsing
2. **Contextual**: Automatic context injection
3. **Secure**: Sensitive data automatically masked
4. **Performant**: Optimized for high-volume logging
5. **Integrated**: Works with existing logging infrastructure

## Common Issues

**Logs not appearing?**
- Check log level: `configure_structured_logging(log_level="DEBUG")`
- Verify file permissions in `logs/` directory

**Context not showing?**
- Ensure you're inside a context manager or have bound context
- Context is thread-local (bind in the same thread you log from)

**Performance issues?**
- Use production setup: `setup_production_logging()`
- Disable console output in production
- Reduce log level to INFO or WARNING

## Support

For questions or issues:
1. Check the [Troubleshooting section](STRUCTURED_LOGGING_GUIDE.md#troubleshooting)
2. Review [examples.py](examples.py) for working code
3. Read the full [Guide](STRUCTURED_LOGGING_GUIDE.md)
