# Diagnostics Export Tool

Comprehensive diagnostics export tool for the Scraper Platform. Collects system information, platform configuration, run history, logs, and performance metrics for troubleshooting and support.

## Overview

The Diagnostics Exporter provides:

- **System Information**: OS, Python version, CPU, memory, disk usage
- **Platform Configuration**: Version, Git info, config files
- **Database Diagnostics**: Schema version, table counts, connection info
- **Run History**: Recent runs with stats and performance data
- **Logs**: Recent logs with error/warning counts (sanitized)
- **Environment Variables**: Sanitized environment configuration
- **Installed Packages**: Complete pip freeze output
- **Performance Metrics**: CPU, memory, process info
- **Recent Errors**: Last 100 error-level log entries

All exports automatically scrub sensitive data (passwords, tokens, API keys, secrets).

## Usage

### CLI Interface

```bash
# Export as ZIP bundle (default, recommended)
python -m src.devtools.diagnostics_exporter --output ./diagnostics.zip

# Export as JSON for programmatic access
python -m src.devtools.diagnostics_exporter --format json --output diagnostics.json

# Export as HTML report for human reading
python -m src.devtools.diagnostics_exporter --format html --output report.html

# Export diagnostics for specific run
python -m src.devtools.diagnostics_exporter --run-id RUN-20251213-ABC123 --format html

# Enable verbose logging
python -m src.devtools.diagnostics_exporter --verbose --output diagnostics.zip
```

### UI Interface

**Method 1: Menu Bar**
1. Open the Scraper Platform UI
2. Click **File** → **Export Diagnostics...**
3. Select format and output path
4. Click **Export**

**Method 2: Settings Page**
1. Navigate to **Settings & Environment** page
2. Click **Export Diagnostics** button
3. Configure export options
4. Click **Export**

### Python API

```python
from pathlib import Path
from src.devtools.diagnostics_exporter import DiagnosticsExporter

# Create exporter
exporter = DiagnosticsExporter(
    output_path=Path("diagnostics.zip"),
    format="zip",
    run_id=None,  # Optional: filter by run_id
)

# Collect all diagnostics
diagnostics = exporter.collect_all()

# Export
output_file = exporter.export()
print(f"Exported to: {output_file}")

# Access individual sections
system_info = exporter._collect_system_info()
run_history = exporter._collect_run_history()
logs = exporter._collect_logs()
```

## Export Formats

### ZIP Bundle (Recommended)

Contains:
- `diagnostics.json` - Complete diagnostics in JSON format
- `sections/*.json` - Individual sections as separate JSON files
- `report.html` - Human-readable HTML report
- `logs/` - Recent log files (last 1000 lines, sanitized)

**Advantages:**
- Complete package with all data
- Easy to share with support
- Includes both machine and human-readable formats
- Compressed for smaller file size

### JSON

Single JSON file with all diagnostic data.

**Advantages:**
- Programmatic access
- Easy to parse and analyze
- Can be imported into other tools

**Use cases:**
- Automated monitoring
- Integration with external systems
- Custom analysis scripts

### HTML Report

Formatted HTML document with tables, charts, and metrics.

**Advantages:**
- Human-readable
- No special tools required (open in any browser)
- Visual presentation of data
- Easy to share via email

**Use cases:**
- Support tickets
- Incident reports
- Internal documentation

## Data Collection

### System Information

- Operating system (name, version, platform)
- Python version and implementation
- CPU (cores, frequency, usage)
- Memory (total, available, used)
- Disk (total, free, used)

### Platform Information

- Platform version
- Working directory
- Git branch and commit info
- Uncommitted changes status
- Configuration files present

### Database Diagnostics

- Schema version
- Database enabled status
- Connection string (sanitized)
- Table names and sizes
- Total table count

### Run History

- Recent runs (last 50 by default)
- Run statistics (status, duration, records)
- Grouped by source and status
- Per-run details (if run_id filter used)

### Logs

- Last 1000 log lines
- Error and warning counts
- Log file locations and sizes
- Fully sanitized (secrets removed)

### Environment Variables

- All environment variables
- Sensitive values redacted
- Count of total vs redacted variables

### Installed Packages

- Complete pip freeze output
- Version numbers
- Package count

### Performance Metrics

- Current CPU and memory usage
- Process-level metrics (PID, threads, memory)
- Run-specific performance (if run_id filter used)

### Recent Errors

- Last 100 error-level log entries
- Timestamp, logger, message
- Metadata (sanitized)

## Security & Privacy

### Automatic Secret Scrubbing

The exporter automatically redacts:

**Patterns:**
- Passwords
- API keys
- Tokens
- Secrets
- Authorization headers
- Bearer tokens
- Database connection strings
- AWS credentials

**Environment Variables:**
- Any variable containing: PASSWORD, SECRET, TOKEN, KEY, CREDENTIALS, AUTH
- Database passwords
- Cloud provider credentials

**Example:**
```
Before: DATABASE_URL=postgresql://user:mypassword123@localhost/db
After:  DATABASE_URL=postgresql://user:***REDACTED***@localhost/db

Before: OPENAI_API_KEY=sk-abc123xyz789
After:  OPENAI_API_KEY=***REDACTED***
```

### Size Limits

- Maximum bundle size: 50 MB
- Maximum log lines: 1000 per file
- Prevents accidentally exporting huge files
- Warnings logged if limits exceeded

### Data Sanitization

All data is sanitized before export:
1. Environment variables checked against secret list
2. Log messages scrubbed with regex patterns
3. Configuration values redacted if sensitive
4. Connection strings have passwords removed

## Examples

### Example 1: Support Ticket

```bash
# Export comprehensive diagnostics for support
python -m src.devtools.diagnostics_exporter \
  --format zip \
  --output support_ticket_12345.zip \
  --verbose

# Attach support_ticket_12345.zip to ticket
```

### Example 2: Incident Investigation

```bash
# Export diagnostics for failed run
python -m src.devtools.diagnostics_exporter \
  --run-id RUN-20251213-FAILED \
  --format html \
  --output incident_report.html

# Review incident_report.html in browser
```

### Example 3: Performance Analysis

```python
from src.devtools.diagnostics_exporter import DiagnosticsExporter

# Collect performance metrics
exporter = DiagnosticsExporter()
perf = exporter._collect_performance_metrics()

print(f"CPU: {perf['current_cpu_percent']}%")
print(f"Memory: {perf['current_memory_percent']}%")
print(f"Process Memory: {perf['process_info']['memory_mb']} MB")
```

### Example 4: Automated Monitoring

```python
import schedule
from pathlib import Path
from datetime import datetime
from src.devtools.diagnostics_exporter import DiagnosticsExporter

def export_daily_diagnostics():
    """Export diagnostics daily for monitoring."""
    timestamp = datetime.now().strftime("%Y%m%d")
    output_path = Path(f"monitoring/diagnostics_{timestamp}.json")

    exporter = DiagnosticsExporter(
        output_path=output_path,
        format="json"
    )

    exporter.export()
    print(f"Daily diagnostics exported: {output_path}")

# Schedule daily export at 2 AM
schedule.every().day.at("02:00").do(export_daily_diagnostics)
```

## Troubleshooting

### Export Fails with Permission Error

**Problem:** Cannot write to output path

**Solution:**
```bash
# Use a directory you have write access to
python -m src.devtools.diagnostics_exporter \
  --output ~/Downloads/diagnostics.zip
```

### Export Too Large

**Problem:** ZIP bundle exceeds 50 MB limit

**Solution:**
```bash
# Use JSON format (smaller, no log files)
python -m src.devtools.diagnostics_exporter \
  --format json \
  --output diagnostics.json

# Or filter by specific run
python -m src.devtools.diagnostics_exporter \
  --run-id RUN-20251213-ABC123 \
  --format zip
```

### Database Connection Failed

**Problem:** Cannot collect database diagnostics

**Solution:**
- Check `DATABASE_URL` environment variable
- Verify database is running
- Check credentials and permissions
- Export will continue with other data even if DB fails

### Missing Log Files

**Problem:** Log files not included in export

**Solution:**
- Check log files exist in `logs/` directory
- Verify file permissions
- Check disk space
- Individual log file failures don't stop overall export

## Integration

### CI/CD Pipeline

```yaml
# .github/workflows/diagnostics.yml
name: Export Diagnostics

on:
  workflow_dispatch:  # Manual trigger
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Export diagnostics
        run: |
          python -m src.devtools.diagnostics_exporter \
            --format json \
            --output diagnostics.json

      - name: Upload artifact
        uses: actions/upload-artifact@v2
        with:
          name: diagnostics
          path: diagnostics.json
```

### Docker Container

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Export diagnostics on container start
CMD ["python", "-m", "src.devtools.diagnostics_exporter", \
     "--format", "json", \
     "--output", "/output/diagnostics.json"]
```

### Kubernetes CronJob

```yaml
# kubernetes/diagnostics-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: diagnostics-export
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: exporter
            image: scraper-platform:latest
            command:
            - python
            - -m
            - src.devtools.diagnostics_exporter
            - --format
            - json
            - --output
            - /output/diagnostics.json
            volumeMounts:
            - name: output
              mountPath: /output
          volumes:
          - name: output
            persistentVolumeClaim:
              claimName: diagnostics-pvc
          restartPolicy: OnFailure
```

## API Reference

### DiagnosticsExporter

```python
class DiagnosticsExporter:
    def __init__(
        self,
        output_path: Optional[Path] = None,
        format: str = "zip",
        run_id: Optional[str] = None,
    ) -> None:
        """
        Initialize the diagnostics exporter.

        Args:
            output_path: Path to export file
            format: Export format ('zip', 'json', 'html')
            run_id: Optional run ID to filter diagnostics
        """

    def collect_all(self) -> Dict[str, Any]:
        """Collect all diagnostic information."""

    def export(self) -> Path:
        """Export diagnostics in the specified format."""

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information."""

    def _collect_platform_info(self) -> Dict[str, Any]:
        """Collect platform version and configuration."""

    def _collect_database_info(self) -> Dict[str, Any]:
        """Collect database diagnostics."""

    def _collect_run_history(self) -> Dict[str, Any]:
        """Collect run history from database."""

    def _collect_logs(self) -> Dict[str, Any]:
        """Collect recent logs."""

    def _collect_environment(self) -> Dict[str, Any]:
        """Collect environment variables (sanitized)."""

    def _collect_installed_packages(self) -> Dict[str, Any]:
        """Collect installed Python packages."""

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect recent performance metrics."""

    def _collect_recent_errors(self) -> Dict[str, Any]:
        """Collect recent error logs."""
```

## Best Practices

1. **Regular Exports**: Schedule weekly exports for monitoring
2. **Incident Response**: Export immediately after issues for investigation
3. **Support Tickets**: Always attach diagnostics to support requests
4. **Version Control**: Don't commit diagnostics exports (add to .gitignore)
5. **Sharing**: Use ZIP format when sharing with others
6. **Analysis**: Use JSON format for automated analysis
7. **Documentation**: Use HTML format for internal documentation

## Related Documentation

- [Logging Configuration](./LOGGING.md)
- [Performance Monitoring](./PERFORMANCE.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
