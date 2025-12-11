# Airflow Setup Guide

## Problem: ERR_CONNECTION_REFUSED

If you see "ERR_CONNECTION_REFUSED" in the Airflow DAG tab, it means Airflow is not running.

## Quick Fix

### Option 1: Start Airflow (Recommended for Full Features)

1. **Install Airflow** (if not already installed):
   ```bash
   pip install apache-airflow
   ```

2. **Initialize Airflow** (first time only):
   ```bash
   export AIRFLOW_HOME=~/airflow
   airflow db init
   airflow users create \
       --username admin \
       --password admin \
       --firstname Admin \
       --lastname User \
       --role Admin
   ```

3. **Start Airflow Webserver** (Terminal 1):
   ```bash
   airflow webserver --port 8080
   ```

4. **Start Airflow Scheduler** (Terminal 2):
   ```bash
   airflow scheduler
   ```

5. **Access Airflow**:
   - Open http://localhost:8080 in browser
   - Or use the desktop UI's "Airflow DAGs" tab
   - Click "Check Connection" to verify
   - Click "Connect" to load the Airflow UI

### Option 2: Use Desktop UI Without Airflow

You can use the desktop UI to run pipelines directly **without Airflow**:

1. Use the **Jobs** tab to start pipelines
2. Pipelines run directly via `run_pipeline()` function
3. No Airflow required for basic operation

## Troubleshooting

### "Connection Refused" Error

**Cause**: Airflow webserver is not running.

**Solution**:
```bash
# Check if Airflow is installed
pip list | grep airflow

# If not installed:
pip install apache-airflow

# Start webserver
airflow webserver --port 8080
```

### "Module not found: airflow"

**Cause**: Airflow is not installed.

**Solution**:
```bash
pip install apache-airflow
```

### Port 8080 Already in Use

**Cause**: Another service is using port 8080.

**Solution**:
```bash
# Use a different port
airflow webserver --port 8081

# Then update the URL in the UI to: http://localhost:8081
```

### Airflow DAGs Not Showing

**Cause**: DAGs folder not configured or DAGs not discovered.

**Solution**:
1. Check `AIRFLOW_HOME` environment variable
2. Ensure DAGs are in `$AIRFLOW_HOME/dags/` or configured path
3. Check Airflow logs for DAG parsing errors

## Using Airflow with Desktop UI

### Step 1: Start Airflow

```bash
# Terminal 1
airflow webserver --port 8080

# Terminal 2  
airflow scheduler
```

### Step 2: Connect in Desktop UI

1. Open the desktop UI: `python run_ui.py`
2. Go to **Airflow DAGs** tab
3. Click **"Check Connection"** to verify Airflow is running
4. Click **"Connect"** to load the Airflow webserver UI
5. You can now:
   - View DAGs
   - Trigger DAGs
   - View task logs
   - Monitor runs

### Step 3: Trigger DAGs

**Via Airflow UI (in webview)**:
- Click the "Play" button on a DAG
- Configure run parameters
- Monitor execution

**Via Desktop UI Controls** (when implemented):
- Use "Pause DAG" / "Resume DAG" buttons
- View DAG status

## Airflow DAG Configuration

Your DAGs are located in:
```
dags/
├── scraper_alfabeta.py
├── scraper_argentina_v5.py
├── scraper_chile_v5.py
├── scraper_lafa_v5.py
└── scraper_quebec_v5.py
```

These DAGs use the unified pipeline runner and can be triggered from Airflow UI.

## Alternative: Run Without Airflow

If you don't want to use Airflow, you can run pipelines directly:

```bash
# Via CLI
python main.py --source alfabeta --env dev

# Via Python API
from src.entrypoints.run_pipeline import run_pipeline
result = run_pipeline(source="alfabeta", environment="dev")

# Via Desktop UI
# Use the Jobs tab - no Airflow needed
```

## Status Indicators in UI

The Airflow tab shows connection status:

- ✅ **Green**: Connected and working
- ⚠️ **Yellow**: Responding but may have issues  
- ❌ **Red**: Connection refused - Airflow not running

Use the **"Check Connection"** button to verify Airflow is accessible before connecting.

## Summary

- **ERR_CONNECTION_REFUSED** = Airflow not running
- **Solution**: Start `airflow webserver --port 8080` and `airflow scheduler`
- **Alternative**: Use desktop UI Jobs tab to run pipelines without Airflow
- **Check**: Use "Check Connection" button in UI to verify Airflow status

