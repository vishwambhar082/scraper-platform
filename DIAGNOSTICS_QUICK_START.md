# Diagnostics Export - Quick Start Guide

Quick reference for exporting platform diagnostics.

## CLI Usage

```bash
# Export as ZIP (recommended)
python -m src.devtools.diagnostics_exporter --output diagnostics.zip

# Export as JSON
python -m src.devtools.diagnostics_exporter --format json --output diagnostics.json

# Export as HTML report
python -m src.devtools.diagnostics_exporter --format html --output report.html

# Export for specific run
python -m src.devtools.diagnostics_exporter --run-id RUN-20251213-ABC123

# Enable verbose output
python -m src.devtools.diagnostics_exporter --verbose
```

## UI Usage

**Method 1: Menu Bar**
1. File → Export Diagnostics...
2. Select format and output path
3. Click Export

**Method 2: Settings Page**
1. Navigate to Settings & Environment
2. Click "Export Diagnostics" button
3. Configure options and export

## Python API

```python
from pathlib import Path
from src.devtools.diagnostics_exporter import DiagnosticsExporter

# Basic usage
exporter = DiagnosticsExporter(
    output_path=Path("diagnostics.zip"),
    format="zip",
)
output_file = exporter.export()

# Export for specific run
exporter = DiagnosticsExporter(
    output_path=Path("diagnostics.html"),
    format="html",
    run_id="RUN-20251213-ABC123",
)
output_file = exporter.export()

# Collect specific sections
exporter = DiagnosticsExporter()
system_info = exporter._collect_system_info()
run_history = exporter._collect_run_history()
logs = exporter._collect_logs()
```

## What Gets Exported

- ✅ System information (OS, Python, CPU, memory)
- ✅ Platform configuration and version
- ✅ Database schema and tables
- ✅ Run history with statistics
- ✅ Recent logs (sanitized)
- ✅ Environment variables (secrets redacted)
- ✅ Installed packages
- ✅ Performance metrics
- ✅ Recent errors

## Export Formats

| Format | Use Case | Contents |
|--------|----------|----------|
| **ZIP** | Support tickets, comprehensive export | JSON + HTML + logs |
| **JSON** | Programmatic access, automation | Machine-readable data |
| **HTML** | Human review, documentation | Formatted report |

## Security

All sensitive data is **automatically redacted**:
- Passwords
- API keys and tokens
- Database credentials
- Authorization headers
- AWS/cloud credentials

## Common Scenarios

### Support Ticket
```bash
python -m src.devtools.diagnostics_exporter \
  --format zip \
  --output support_ticket_12345.zip
```

### Failed Run Investigation
```bash
python -m src.devtools.diagnostics_exporter \
  --run-id RUN-20251213-FAILED \
  --format html \
  --output incident_report.html
```

### Performance Analysis
```bash
python -m src.devtools.diagnostics_exporter \
  --format json \
  --output performance_analysis.json
```

## Output Files

### ZIP Bundle
```
diagnostics.zip
├── diagnostics.json          # Complete data
├── sections/                 # Individual sections
│   ├── system.json
│   ├── platform.json
│   ├── database.json
│   ├── runs.json
│   ├── logs.json
│   └── ...
├── report.html               # Human-readable report
└── logs/                     # Recent log files
    ├── unified_logs.jsonl
    └── scraper.log
```

### JSON Export
```json
{
  "metadata": { "exported_at": "2025-12-13T10:30:00", ... },
  "system": { "os": {...}, "python": {...}, "cpu": {...}, ... },
  "platform": { "version": "5.0.0", "git": {...}, ... },
  "database": { "schema_version": 3, "tables": [...], ... },
  "runs": { "total_runs": 42, "by_status": {...}, ... },
  "logs": { "total_lines": 1000, "error_count": 5, ... },
  "environment": { "variables": {...}, "count": 50, ... },
  "packages": { "packages": [...], "total_count": 120, ... },
  "performance": { "current_cpu_percent": 15.2, ... },
  "errors": { "errors": [...], "total_count": 5 }
}
```

## Troubleshooting

**Problem: Permission denied**
```bash
# Use a directory you have write access to
python -m src.devtools.diagnostics_exporter --output ~/Downloads/diagnostics.zip
```

**Problem: File too large**
```bash
# Use JSON format (smaller, no log files)
python -m src.devtools.diagnostics_exporter --format json

# Or filter by specific run
python -m src.devtools.diagnostics_exporter --run-id RUN-20251213-ABC123
```

**Problem: Database connection failed**
- Check DATABASE_URL environment variable
- Verify database is running
- Export will continue with other data

## More Information

See [docs/DIAGNOSTICS_EXPORT.md](docs/DIAGNOSTICS_EXPORT.md) for complete documentation.
