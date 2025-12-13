# Structured Logging Guide

Comprehensive guide for using structured JSON logging in the Scraper Platform.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Context Management](#context-management)
4. [Advanced Features](#advanced-features)
5. [Migration Guide](#migration-guide)
6. [Performance Optimization](#performance-optimization)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

The required dependency is already included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Basic Setup

```python
from src.app_logging.structured_logger import (
    configure_structured_logging,
    get_structured_logger,
)

# Configure logging (do this once at application startup)
configure_structured_logging(
    log_level="INFO",
    enable_console=True,
    enable_file=True,
)

# Get a logger
log = get_structured_logger(__name__)

# Log messages
log.info("application_started", version="5.0", environment="production")
```

### Output Example

```json
{
  "timestamp": "2025-12-13T19:45:23.123456Z",
  "level": "INFO",
  "logger": "my_module",
  "event": "application_started",
  "version": "5.0",
  "environment": "production"
}
```

---

## Basic Usage

### Simple Logging

```python
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

# Different log levels
log.debug("debug_message", detail="Additional debug info")
log.info("info_message", user_id=12345)
log.warning("warning_message", threshold_exceeded=True)
log.error("error_message", error_code="ERR_001")
log.critical("critical_message", system="database")

# Exception logging with automatic traceback
try:
    result = 1 / 0
except Exception:
    log.exception("division_error", numerator=1, denominator=0)
```

### Structured Event Logging

```python
# Scraping events
log.info(
    "scrape_started",
    source="alfabeta",
    run_id="12345",
    url="https://example.com",
    max_pages=100,
)

log.info(
    "scrape_completed",
    source="alfabeta",
    run_id="12345",
    pages_scraped=95,
    items_extracted=1250,
    duration_seconds=45.3,
)

# Pipeline events
log.info(
    "step_started",
    step_id="fetch_data",
    step_type="FETCH",
    step_index=0,
)

log.info(
    "step_completed",
    step_id="fetch_data",
    step_type="FETCH",
    duration_ms=234.5,
    items_processed=100,
)
```

---

## Context Management

Context variables are automatically included in all log entries within a scope.

### Thread-Local Context

```python
from src.app_logging.log_context import bind_context, unbind_context, clear_context
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

# Bind context for all subsequent logs
bind_context(run_id="12345", source="alfabeta")

log.info("step_1_started")  # Includes run_id and source
log.info("step_2_started")  # Also includes run_id and source

# Unbind specific keys
unbind_context("source")

log.info("step_3_started")  # Only includes run_id

# Clear all context
clear_context()

log.info("step_4_started")  # No context variables
```

### Context Decorators

```python
from src.app_logging.log_context import log_context, with_context_from_kwargs
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

# Automatic context binding for function duration
@log_context(source="alfabeta", job_id="daily_scrape")
def scrape_alfabeta():
    log.info("scrape_started")  # Includes source and job_id
    # ... scraping logic ...
    log.info("scrape_completed")  # Also includes source and job_id


# Extract context from function arguments
@with_context_from_kwargs("run_id", "source")
def process_scrape(run_id: str, source: str, data: dict):
    log.info("processing_started")  # Includes run_id and source from args
    # ... processing logic ...
    log.info("processing_completed")


# Usage
scrape_alfabeta()
process_scrape(run_id="12345", source="alfabeta", data={})
```

### Context Managers

```python
from src.app_logging.log_context import (
    context_scope,
    nested_context,
    isolated_context,
)
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

# Scoped context (temporary)
with context_scope(run_id="12345", source="alfabeta"):
    log.info("inside_scope")  # Includes run_id and source

log.info("outside_scope")  # No context variables


# Nested context (adds to existing context)
bind_context(run_id="12345")

with nested_context(step_id="step_1"):
    log.info("step_1")  # Includes run_id AND step_id

with nested_context(step_id="step_2"):
    log.info("step_2")  # Includes run_id AND step_id (updated)


# Isolated context (ignores parent context)
bind_context(run_id="12345", source="alfabeta")

with isolated_context(task_id="background_task"):
    log.info("isolated_task")  # Only includes task_id

log.info("back_to_parent")  # Includes run_id and source
```

### Specialized Context Managers

```python
from src.app_logging.log_context import RunContext, StepContext, TaskContext
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

# Run context
with RunContext(run_id="12345", source="alfabeta", environment="production"):
    log.info("run_started")
    # ... scraping logic ...
    log.info("run_completed")


# Step context (nested within run)
with RunContext(run_id="12345", source="alfabeta"):
    with StepContext(step_id="fetch_data", step_type="FETCH", step_index=0):
        log.info("step_started")
        # ... step logic ...
        log.info("step_completed")

    with StepContext(step_id="parse_data", step_type="PARSE", step_index=1):
        log.info("step_started")
        # ... step logic ...
        log.info("step_completed")


# Task context
with TaskContext(task_id="scrape_alfabeta", task_type="scraping"):
    log.info("task_started")
    # ... task logic ...
    log.info("task_completed")
```

---

## Advanced Features

### Sensitive Data Masking

Automatic masking of passwords, tokens, and other sensitive data:

```python
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

# These will be automatically masked
log.info(
    "authentication",
    username="user123",
    password="secret123",  # Automatically masked
    api_key="sk-1234567890",  # Automatically masked
)

# Output:
# {
#   "username": "user123",
#   "password": "***REDACTED***",
#   "api_key": "***REDACTED***"
# }

# URLs with credentials are masked
log.info(
    "proxy_configured",
    proxy_url="http://user:pass@proxy.com:8080",  # Credentials masked
)

# Bearer tokens are masked
log.info(
    "api_request",
    authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  # Masked
)
```

### Exception Logging

```python
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

try:
    # Some operation that might fail
    result = risky_operation()
except ValueError as e:
    log.exception(
        "operation_failed",
        operation="risky_operation",
        input_data={"param": "value"},
    )
    # Automatically includes exception type, message, and full traceback
```

### Custom Processors

Add custom processing logic to logs:

```python
import structlog

def add_hostname(logger, method_name, event_dict):
    """Add hostname to all log events."""
    import socket
    event_dict["hostname"] = socket.gethostname()
    return event_dict

# Configure with custom processor
from src.app_logging.structured_logger import configure_structured_logging

configure_structured_logging(
    log_level="INFO",
    enable_console=True,
)

# Add custom processor
structlog.configure(
    processors=structlog.get_config()["processors"] + [add_hostname],
)
```

### File Rotation

```python
from pathlib import Path
from src.app_logging.structured_logger import configure_structured_logging

# Configure with custom rotation settings
configure_structured_logging(
    log_level="INFO",
    log_dir=Path("logs"),
    json_log_file="scraper.jsonl",
    max_bytes=50 * 1024 * 1024,  # 50 MB
    backup_count=20,  # Keep 20 backup files
    enable_console=True,
    enable_file=True,
)

# Log files will be rotated automatically:
# logs/scraper.jsonl
# logs/scraper.jsonl.1
# logs/scraper.jsonl.2
# ...
# logs/scraper.jsonl.20
```

### Production vs Development Setup

```python
from src.app_logging.structured_logger import (
    setup_production_logging,
    setup_development_logging,
)
import os

# Production setup (optimized for performance)
if os.getenv("ENVIRONMENT") == "production":
    setup_production_logging(
        log_level="INFO",
        log_dir=Path("/var/log/scraper"),
        enable_console=False,  # Only file output
    )
else:
    # Development setup (verbose output)
    setup_development_logging(
        log_level="DEBUG",
        log_dir=Path("logs"),
    )
```

---

## Migration Guide

### From Standard Library Logging

**Before:**
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Scrape started for source: %s", source)
logger.info("Processed %d items in %.2f seconds", item_count, duration)
```

**After:**
```python
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

log.info("scrape_started", source=source)
log.info("scrape_completed", items=item_count, duration_seconds=duration)
```

### From Existing JsonLogFormatter

**Before:**
```python
from src.common.logging_utils import get_logger

log = get_logger(__name__)
log.info(
    "Step started",
    extra={"run_id": run_id, "source": source, "step": "fetch"}
)
```

**After:**
```python
from src.app_logging.structured_logger import get_structured_logger
from src.app_logging.log_context import bind_context

log = get_structured_logger(__name__)

# Option 1: Bind context once
bind_context(run_id=run_id, source=source)
log.info("step_started", step="fetch")

# Option 2: Include in each log
log.info("step_started", run_id=run_id, source=source, step="fetch")
```

### From UnifiedLogger

**Before:**
```python
from src.app_logging.unified_logger import get_unified_logger

logger = get_unified_logger()
logger.log(
    level="INFO",
    message="Scrape completed",
    source="alfabeta",
    run_id="12345",
    metadata={"items": 100, "duration": 45.3},
)
```

**After:**
```python
from src.app_logging.structured_logger import get_global_structured_logger

logger = get_global_structured_logger()
logger.info(
    "scrape_completed",
    source="alfabeta",
    run_id="12345",
    items=100,
    duration=45.3,
)
```

### Gradual Migration Strategy

You can use both systems simultaneously during migration:

```python
from src.app_logging.structured_logger import (
    configure_structured_logging,
    StructuredUnifiedLogger,
)
from src.app_logging.unified_logger import get_unified_logger

# Configure structured logging
configure_structured_logging()

# Create adapter that logs to both systems
unified_logger = get_unified_logger()
logger = StructuredUnifiedLogger(unified_logger=unified_logger)

# This logs to both structured logger AND unified logger
logger.info(
    "scrape_started",
    source="alfabeta",
    run_id="12345",
)

# Logs appear in:
# 1. logs/scraper_structured.jsonl (structured)
# 2. logs/unified_logs.jsonl (unified logger)
# 3. logs/unified_logs.db (unified logger database)
```

---

## Performance Optimization

### High-Volume Logging

For high-throughput scenarios (thousands of logs per second):

```python
from pathlib import Path
from src.app_logging.structured_logger import configure_structured_logging

configure_structured_logging(
    log_level="INFO",
    log_dir=Path("logs"),
    enable_console=False,  # Disable console for performance
    enable_file=True,
    enable_caller_info=False,  # Disable caller info (expensive)
    cache_logger_on_first_use=True,  # Enable caching
)
```

### Lazy Evaluation

Avoid expensive operations when log level is disabled:

```python
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

# Bad: expensive_function() always executes
log.debug("debug_info", data=expensive_function())

# Good: only executes if DEBUG level is enabled
if log.isEnabledFor(logging.DEBUG):
    log.debug("debug_info", data=expensive_function())
```

### Batch Context Binding

```python
from src.app_logging.log_context import bind_context
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

# Bind context once for multiple logs
context = {
    "run_id": "12345",
    "source": "alfabeta",
    "job_id": "daily_scrape",
    "environment": "production",
}

bind_context(**context)

# All subsequent logs include context (no overhead)
for i in range(1000):
    log.info("item_processed", item_id=i)
```

---

## Best Practices

### 1. Use Consistent Event Names

Use lowercase with underscores for event names:

```python
# Good
log.info("scrape_started")
log.info("step_completed")
log.error("validation_failed")

# Avoid
log.info("Scrape Started")
log.info("stepCompleted")
log.error("Validation-Failed")
```

### 2. Use Structured Fields, Not String Formatting

```python
# Good
log.info("scrape_completed", items=100, duration_seconds=45.3)

# Avoid
log.info(f"Scrape completed with {items} items in {duration} seconds")
```

### 3. Bind Context Early

Bind context at the start of operations:

```python
from src.app_logging.log_context import RunContext
from src.app_logging.structured_logger import get_structured_logger

log = get_structured_logger(__name__)

def scrape_source(run_id: str, source: str):
    # Bind context at the start
    with RunContext(run_id=run_id, source=source):
        log.info("scrape_started")
        # All logs automatically include run_id and source
        fetch_data()
        parse_data()
        export_data()
        log.info("scrape_completed")
```

### 4. Use Appropriate Log Levels

- **DEBUG**: Detailed diagnostic information (disabled in production)
- **INFO**: General informational messages (key events)
- **WARNING**: Warning messages (degraded functionality)
- **ERROR**: Error messages (operation failed but app continues)
- **CRITICAL**: Critical messages (system failure)

```python
log.debug("request_details", url=url, headers=headers)
log.info("scrape_started", source=source)
log.warning("rate_limit_approaching", requests_remaining=10)
log.error("parse_error", error=str(e), raw_data=data)
log.critical("database_connection_failed", error=str(e))
```

### 5. Include Relevant Metadata

Always include context that helps debugging:

```python
# Good
log.error(
    "api_request_failed",
    url=url,
    status_code=response.status_code,
    response_body=response.text[:500],
    retry_count=3,
)

# Insufficient
log.error("API request failed")
```

### 6. Use Exception Logging

Always use `log.exception()` in exception handlers:

```python
# Good
try:
    result = risky_operation()
except Exception:
    log.exception("operation_failed", operation="risky_operation")

# Missing traceback
try:
    result = risky_operation()
except Exception as e:
    log.error("operation_failed", error=str(e))
```

### 7. Avoid Logging Sensitive Data

Sensitive fields are automatically masked, but follow these guidelines:

```python
# Automatic masking
log.info("user_authenticated", username="user123", password="secret")
# Output: {"username": "user123", "password": "***REDACTED***"}

# Manual masking for custom sensitive data
log.info(
    "api_key_generated",
    key_id="key_123",
    key_value="***REDACTED***",  # Manually redact
)
```

---

## Troubleshooting

### Logs Not Appearing

1. Check log level configuration:
   ```python
   configure_structured_logging(log_level="DEBUG")  # Lower log level
   ```

2. Verify logger name:
   ```python
   log = get_structured_logger(__name__)  # Use module name
   ```

3. Check file permissions:
   ```bash
   ls -la logs/
   # Ensure write permissions
   ```

### Context Not Appearing in Logs

1. Verify context is bound:
   ```python
   from src.app_logging.log_context import get_context
   print(get_context())  # Should show bound variables
   ```

2. Check thread context isolation:
   ```python
   # Context is thread-local
   # Make sure you bind in the same thread where you log
   ```

3. Use context managers correctly:
   ```python
   # Inside the context
   with context_scope(run_id="12345"):
       log.info("message")  # Has context

   log.info("message")  # No context (outside scope)
   ```

### Performance Issues

1. Disable caller info in production:
   ```python
   configure_structured_logging(enable_caller_info=False)
   ```

2. Reduce log level:
   ```python
   configure_structured_logging(log_level="INFO")  # Not DEBUG
   ```

3. Disable console output:
   ```python
   configure_structured_logging(enable_console=False)
   ```

### Log Files Growing Too Large

1. Configure rotation:
   ```python
   configure_structured_logging(
       max_bytes=10 * 1024 * 1024,  # 10 MB
       backup_count=5,  # Keep 5 backups
   )
   ```

2. Use external log rotation (logrotate):
   ```bash
   # /etc/logrotate.d/scraper
   /var/log/scraper/*.jsonl {
       daily
       rotate 30
       compress
       delaycompress
       notifempty
       create 0644 scraper scraper
   }
   ```

---

## Complete Example

Here's a complete example of using structured logging in a scraper:

```python
from pathlib import Path
from src.app_logging.structured_logger import (
    configure_structured_logging,
    get_structured_logger,
)
from src.app_logging.log_context import RunContext, StepContext


# Configure logging at application startup
def setup_logging():
    configure_structured_logging(
        log_level="INFO",
        log_dir=Path("logs"),
        enable_console=True,
        enable_file=True,
        enable_caller_info=False,  # Production optimization
    )


# Scraper implementation
class AlfabetaScraper:
    def __init__(self):
        self.log = get_structured_logger(__name__)

    def scrape(self, run_id: str):
        with RunContext(run_id=run_id, source="alfabeta", environment="production"):
            self.log.info("scrape_started", max_pages=100)

            try:
                # Step 1: Fetch
                with StepContext(step_id="fetch", step_type="FETCH", step_index=0):
                    data = self._fetch_data()
                    self.log.info("fetch_completed", pages_fetched=len(data))

                # Step 2: Parse
                with StepContext(step_id="parse", step_type="PARSE", step_index=1):
                    items = self._parse_data(data)
                    self.log.info("parse_completed", items_extracted=len(items))

                # Step 3: Export
                with StepContext(step_id="export", step_type="EXPORT", step_index=2):
                    self._export_data(items)
                    self.log.info("export_completed", items_exported=len(items))

                self.log.info("scrape_completed", total_items=len(items))

            except Exception as e:
                self.log.exception("scrape_failed", error=str(e))
                raise

    def _fetch_data(self):
        # Fetch implementation
        return ["page1", "page2", "page3"]

    def _parse_data(self, data):
        # Parse implementation
        return [{"id": 1}, {"id": 2}]

    def _export_data(self, items):
        # Export implementation
        pass


# Main application
if __name__ == "__main__":
    setup_logging()

    scraper = AlfabetaScraper()
    scraper.scrape(run_id="12345")
```

**Output (logs/scraper_structured.jsonl):**

```json
{"timestamp":"2025-12-13T19:45:23.123456Z","level":"INFO","logger":"__main__","event":"scrape_started","run_id":"12345","source":"alfabeta","environment":"production","max_pages":100}
{"timestamp":"2025-12-13T19:45:24.234567Z","level":"INFO","logger":"__main__","event":"fetch_completed","run_id":"12345","source":"alfabeta","environment":"production","step_id":"fetch","step_type":"FETCH","step_index":0,"pages_fetched":3}
{"timestamp":"2025-12-13T19:45:25.345678Z","level":"INFO","logger":"__main__","event":"parse_completed","run_id":"12345","source":"alfabeta","environment":"production","step_id":"parse","step_type":"PARSE","step_index":1,"items_extracted":2}
{"timestamp":"2025-12-13T19:45:26.456789Z","level":"INFO","logger":"__main__","event":"export_completed","run_id":"12345","source":"alfabeta","environment":"production","step_id":"export","step_type":"EXPORT","step_index":2,"items_exported":2}
{"timestamp":"2025-12-13T19:45:27.567890Z","level":"INFO","logger":"__main__","event":"scrape_completed","run_id":"12345","source":"alfabeta","environment":"production","total_items":2}
```

---

## Integration with Observability Tools

### Elasticsearch/ELK Stack

```python
# Logs are already in JSON format (newline-delimited)
# Use Filebeat to ship logs to Elasticsearch

# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/scraper/*.jsonl
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["localhost:9200"]
```

### Grafana Loki

```python
# Use Promtail to ship logs to Loki

# promtail.yml
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: scraper
    static_configs:
      - targets:
          - localhost
        labels:
          job: scraper
          __path__: /var/log/scraper/*.jsonl
    pipeline_stages:
      - json:
          expressions:
            level: level
            timestamp: timestamp
      - labels:
          level:
```

### CloudWatch Logs

```python
# Use AWS CloudWatch agent

# config.json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/scraper/*.jsonl",
            "log_group_name": "/scraper/structured",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

---

## Summary

Structured logging provides:
- **Machine-readable** JSON format for easy parsing and analysis
- **Context management** for automatic field injection
- **Sensitive data masking** for security
- **Performance optimization** for high-volume logging
- **Integration** with existing logging infrastructure
- **Observability** for modern monitoring tools

For more information, see:
- `src/app_logging/structured_logger.py` - Core implementation
- `src/app_logging/log_context.py` - Context management
- `src/app_logging/unified_logger.py` - Existing unified logger
