# Developer Tools

Developer tooling suite for the Scraper Platform, providing debugging, replay, and diagnostics capabilities.

## Contents

- **browser_replay.py** - Browser interaction replay for debugging
- **history_replay.py** - Historical run replay functionality
- **screenshot_diff.py** - Visual regression testing
- **diagnostics_exporter.py** - Comprehensive diagnostics export tool
- **hoverfly_simulator.py** - HTTP traffic simulation
- **mitmproxy_hooks.py** - MITM proxy integration

## Diagnostics Exporter

Export comprehensive platform diagnostics for troubleshooting and support.

### Quick Start

```bash
# CLI export
python -m src.devtools.diagnostics_exporter --output diagnostics.zip

# Python API
from src.devtools.diagnostics_exporter import DiagnosticsExporter

exporter = DiagnosticsExporter(output_path="diagnostics.zip")
exporter.export()
```

### Features

- System information (OS, Python, CPU, memory, disk)
- Platform configuration (version, Git, config files)
- Database diagnostics (schema, tables, connections)
- Run history with statistics
- Recent logs (sanitized, last 1000 lines)
- Environment variables (secrets redacted)
- Installed packages (pip freeze)
- Performance metrics
- Recent errors

### Export Formats

- **ZIP**: Bundle with JSON, HTML report, and log files (recommended)
- **JSON**: Machine-readable data for programmatic access
- **HTML**: Human-readable report for browsers

### Security

All sensitive data is automatically scrubbed:
- Passwords, API keys, tokens
- Database credentials
- Authorization headers
- AWS credentials
- Any env vars containing: PASSWORD, SECRET, TOKEN, KEY, AUTH

### Documentation

See [docs/DIAGNOSTICS_EXPORT.md](../../docs/DIAGNOSTICS_EXPORT.md) for complete documentation.

## Browser Replay

Replay browser interactions for debugging failed scrapes.

```python
from src.devtools.browser_replay import BrowserReplayer

replayer = BrowserReplayer(run_id="RUN-20251213-ABC123")
replayer.replay()
```

## Screenshot Diff

Visual regression testing for UI changes.

```python
from src.devtools.screenshot_diff import ScreenshotDiff

diff = ScreenshotDiff()
diff.compare(baseline="baseline.png", current="current.png")
```

## History Replay

Replay historical runs for testing and debugging.

```python
from src.devtools.history_replay import HistoryReplay

replay = HistoryReplay(run_id="RUN-20251213-ABC123")
replay.execute()
```

## Best Practices

1. **Export diagnostics** before reporting issues
2. **Include run_id** when debugging specific failures
3. **Use ZIP format** when sharing with support
4. **Review HTML reports** for human analysis
5. **Parse JSON exports** for automated monitoring
6. **Verify secrets are redacted** before sharing

## Related Tools

- [CLI Tools](../cli/README.md)
- [Monitoring](../observability/README.md)
- [Logging](../app_logging/README.md)
