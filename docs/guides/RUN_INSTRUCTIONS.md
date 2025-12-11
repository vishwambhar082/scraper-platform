# Run Instructions - Scraper Platform

## Quick Start

### 1. Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install scraper-specific dependencies
pip install -r scraper-deps/requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```bash
# Database connection (if using)
DATABASE_URL=postgresql://user:password@localhost/scraper_db

# API keys (if needed)
GROQ_API_KEY=your_key_here
SCRAPERAPI_KEY=your_key_here

# Logging
SCRAPER_LOG_LEVEL=INFO
```

### 3. Run Desktop UI

```bash
python run_ui.py
```

The UI will open with:
- Left pane: Jobs, Tasks, Logs, History
- Right pane: Workflow Graph, Airflow DAGs, Status
- Bottom: Console output

### 4. Run via CLI

```bash
# List available scrapers
python main.py --list

# Run a scraper
python main.py --source alfabeta --env dev
```

### 5. Run via Python API

```python
from src.entrypoints.run_pipeline import run_pipeline

result = run_pipeline(
    source="alfabeta",
    run_type="FULL_REFRESH",
    environment="dev",
    params={"max_items": 100}
)

print(f"Status: {result['status']}")
print(f"Run ID: {result['run_id']}")
```

## Running with Airflow

### 1. Install Airflow

```bash
pip install apache-airflow
```

### 2. Initialize Airflow

```bash
export AIRFLOW_HOME=~/airflow
airflow db init
airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin
```

### 3. Start Airflow

```bash
# Terminal 1: Webserver
airflow webserver --port 8080

# Terminal 2: Scheduler
airflow scheduler
```

### 4. Access Airflow UI

Open http://localhost:8080 in browser, or use the desktop UI's Airflow tab.

### 5. Trigger DAGs

- Via Airflow UI: Click "Play" button on a DAG
- Via Desktop UI: Use Airflow tab controls
- Via API: `airflow dags trigger scraper_alfabeta`

## Running Specific Scrapers

### Alfabeta

```bash
python main.py --source alfabeta --env dev
```

### Argentina

```bash
python main.py --source argentina --env dev
```

### Chile

```bash
python main.py --source chile --env dev
```

### Lafa

```bash
python main.py --source lafa --env dev
```

### Quebec

```bash
python main.py --source quebec --env dev
```

## Environment Configuration

### Development

```bash
python main.py --source alfabeta --env dev
```

Uses `config/env/dev.yaml` settings.

### Staging

```bash
python main.py --source alfabeta --env staging
```

Uses `config/env/staging.yaml` settings.

### Production

```bash
python main.py --source alfabeta --env prod
```

Uses `config/env/prod.yaml` settings.

## Viewing Logs

### Unified Logs

```python
from src.app_logging import get_unified_logger

logger = get_unified_logger()

# Search logs
results = logger.search(
    source="alfabeta",
    level="ERROR",
    limit=100
)

# Export to CSV
logger.export_csv(Path("logs_export.csv"))

# Export to JSON
logger.export_json(Path("logs_export.json"))
```

### Log Files

- JSON logs: `logs/unified_logs.jsonl`
- Database: `logs/unified_logs.db`
- Event history: `logs/event_history.json`

### Desktop UI

Use the "Logs" tab in the desktop UI to view and filter logs in real-time.

## Troubleshooting

### UI Won't Start

**Error**: `ModuleNotFoundError: No module named 'PySide6'`

**Solution**:
```bash
pip install PySide6 PySide6-WebEngine
```

### Pipeline Fails

**Check logs**:
```bash
# View recent errors
python -c "from src.app_logging import get_unified_logger; logger = get_unified_logger(); print(logger.search(level='ERROR', limit=10))"
```

**Common issues**:
1. Missing configuration files
2. Database connection issues
3. Missing API keys
4. Network connectivity

### Airflow Connection Fails

**Error**: `ERR_CONNECTION_REFUSED` or "Cannot connect to Airflow webserver"

**Solution**:
1. **Airflow is not running** - This is the most common cause
   ```bash
   # Install Airflow (if not installed)
   pip install apache-airflow
   
   # Start Airflow webserver (Terminal 1)
   airflow webserver --port 8080
   
   # Start Airflow scheduler (Terminal 2)
   airflow scheduler
   ```

2. **Use the UI's "Check Connection" button**:
   - Go to "Airflow DAGs" tab in desktop UI
   - Click "Check Connection" button
   - This will test if Airflow is accessible
   - Status indicator shows: ✅ Green (connected), ❌ Red (not running)

3. **Alternative: Run without Airflow**:
   - Use the "Jobs" tab in desktop UI to run pipelines directly
   - No Airflow required for basic pipeline execution
   - Airflow is only needed for scheduled/orchestrated runs

4. **Verify Airflow is accessible**:
   ```bash
   curl http://localhost:8080/health
   # Or open http://localhost:8080 in browser
   ```

**See `AIRFLOW_SETUP.md` for detailed setup instructions.**

### Import Errors

**Error**: `ImportError: cannot import name 'X'`

**Solution**:
1. Ensure you're in the project root
2. Check that `src/` is in Python path
3. Verify module exists: `ls src/path/to/module.py`

## Development Mode

### Enable Debug Logging

```bash
export SCRAPER_LOG_LEVEL=DEBUG
python run_ui.py
```

### Run Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Type checking (if mypy installed)
mypy src/

# Linting (if pylint installed)
pylint src/
```

## Production Deployment

### 1. Set Environment Variables

```bash
export SCRAPER_ENV=prod
export DATABASE_URL=postgresql://...
export SECRET_KEY=...
```

### 2. Run with Production Config

```bash
python main.py --source alfabeta --env prod
```

### 3. Monitor Logs

```bash
# Tail unified logs
tail -f logs/unified_logs.jsonl

# Query database
sqlite3 logs/unified_logs.db "SELECT * FROM logs WHERE level='ERROR' ORDER BY timestamp DESC LIMIT 10;"
```

## Additional Resources

- **Architecture**: See `consolidated-docs/ARCHITECTURE_V5.md`
- **Workflow**: See `WORKFLOW_DIAGRAM.md`
- **Refactoring Summary**: See `REFACTORING_SUMMARY.md`
- **Airflow Setup**: See `AIRFLOW_SETUP.md` (for ERR_CONNECTION_REFUSED errors)
- **API Documentation**: See `src/api/` modules

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review `consolidated-docs/troubleshooting/`
3. Check error codes in `consolidated-docs/error_codes.md`

