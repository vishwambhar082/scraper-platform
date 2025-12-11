# Airflow Windows Troubleshooting Guide

## Common Issues on Windows

### 1. API Server Exits Immediately

**Symptoms:**
- Scheduler starts successfully
- API server process exits immediately
- Error: "Auth manager is not configured"

**Solution:**

Airflow 3.x requires an auth manager to be configured. Run:

```bash
python tools/setup_airflow_auth.py
```

Or manually edit `C:\Users\<your-username>\airflow\airflow.cfg`:

1. Find the `[core]` section
2. Add or update:
   ```ini
   auth_manager = airflow.api_fastapi.auth.managers.simple.simple_auth_manager.SimpleAuthManager
   ```
3. Restart Airflow services

### 2. Application Freezes When Starting Services

**Fixed:** The UI now uses proper Qt threading (QThread) instead of Python threads, preventing freezes.

If you still experience freezes:
- Check console output for errors
- Ensure Airflow is properly installed
- Try restarting the application

### 3. Windows Compatibility Warnings

**Expected:** Airflow shows warnings on Windows. This is normal and expected.

Airflow officially supports:
- Linux (recommended)
- macOS
- Windows via WSL2 or Docker

For best results on Windows:
- Use WSL2 (Windows Subsystem for Linux 2)
- Or use Docker containers
- Or accept limited functionality on native Windows

### 4. Port 8080 Already in Use

**Solution:**
- Stop other services using port 8080
- Or change the port in `AirflowServiceManager.api_port`

### 5. Database Initialization Issues

**Solution:**
- Airflow 3.x auto-initializes on first run
- Ensure `~/airflow` directory is writable
- Check console for database errors

## Quick Fixes

### Configure Auth Manager

```bash
python tools/setup_airflow_auth.py
```

### Check Airflow Status

```bash
python -m airflow version
python -m airflow db check
```

### Manual Service Start (for debugging)

```bash
# Terminal 1
python -m airflow scheduler

# Terminal 2
python -m airflow api-server --port 8080
```

## Best Practices for Windows

1. **Use WSL2** for production Airflow deployments
2. **Use Docker** for isolated Airflow environments
3. **Accept limitations** if using native Windows (some features may not work)
4. **Check logs** in `~/airflow/logs/` for detailed error messages

## Getting Help

1. Check console output for detailed error messages
2. Review `~/airflow/logs/` directory
3. Check Airflow documentation: https://airflow.apache.org/docs/
4. Windows-specific issues: https://github.com/apache/airflow/issues/10388

