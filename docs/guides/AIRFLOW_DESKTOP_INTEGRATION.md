# Airflow Desktop Integration - Complete Implementation

## Overview

The Scraper Platform Desktop UI now includes **full Airflow integration** with automatic service management. Airflow runs entirely within the desktop application - no browser or separate terminals required.

## Features

✅ **Automatic Service Management**
- Start/Stop Airflow scheduler and API server from the UI
- Services run in background (no console windows)
- Automatic initialization of Airflow database

✅ **Embedded Airflow UI**
- Full Airflow webserver UI embedded in desktop window
- No browser required - everything in one application
- Real-time status indicators

✅ **Service Status Monitoring**
- Visual status indicators (Green/Yellow/Red)
- Connection checking
- Automatic health monitoring

✅ **Clean Shutdown**
- Prompts to stop Airflow services on app close
- Graceful cleanup of background processes

## Architecture

### Components

1. **`src/ui/airflow_service.py`** - AirflowServiceManager
   - Manages Airflow processes (scheduler, API server)
   - Handles process lifecycle
   - Provides status monitoring

2. **`src/ui/main_window.py`** - Updated UI
   - Service management controls
   - Embedded Airflow webview
   - Status indicators

### Service Flow

```
Desktop App Start
    ↓
User clicks "Start Airflow Services"
    ↓
AirflowServiceManager.start_all()
    ├─ Check if Airflow installed
    ├─ Initialize database (if needed)
    ├─ Start scheduler (background process)
    └─ Start API server (background process)
    ↓
Wait for API to be ready
    ↓
Update UI status: "✅ Running"
    ↓
User clicks "Connect"
    ↓
Load Airflow UI in embedded webview
```

## Usage

### Starting Airflow Services

1. **Open the Desktop UI**:
   ```bash
   python run_ui.py
   ```

2. **Go to "Airflow DAGs" tab**

3. **Click "Start Airflow Services"**
   - Services start automatically
   - Status updates to "✅ Running" when ready
   - Takes ~5-10 seconds to initialize

4. **Click "Connect"** to load Airflow UI

### Stopping Airflow Services

1. **Click "Stop Airflow Services"**
2. Confirm the dialog
3. Services stop gracefully

### Automatic Shutdown

When closing the application:
- If Airflow services are running, you'll be prompted to stop them
- Services are cleaned up automatically

## Requirements

### Installation

```bash
# Install Airflow
pip install apache-airflow

# Install UI dependencies (already in requirements.txt)
pip install -r requirements.txt
```

### First-Time Setup

On first run, Airflow will:
1. Create `~/airflow` directory
2. Initialize SQLite database
3. Set up default configuration

**Note**: For production, you may want to configure Airflow to use PostgreSQL instead of SQLite.

## Technical Details

### Process Management

- **Scheduler**: Runs as background subprocess
- **API Server**: Runs on port 8080 (configurable)
- **Process Flags**: Uses `CREATE_NO_WINDOW` on Windows to hide console windows

### Status Monitoring

- **Health Check**: Polls `/health` endpoint
- **Process Check**: Monitors subprocess status
- **Timeout**: 30 seconds for API readiness check

### Error Handling

- **Airflow Not Installed**: Shows helpful error message
- **Port Already in Use**: Error logged, user notified
- **Startup Failures**: Status updated, error messages shown

## Configuration

### Airflow Home Directory

Default: `~/airflow`

To change:
```python
from src.ui.airflow_service import AirflowServiceManager

service = AirflowServiceManager(airflow_home=Path("/custom/path/airflow"))
```

### API Port

Default: `8080`

To change:
```python
service = AirflowServiceManager()
service.api_port = 8081
```

## Troubleshooting

### "Airflow Not Installed"

**Solution**:
```bash
pip install apache-airflow
```

### "Port 8080 Already in Use"

**Solution**:
- Stop other services using port 8080
- Or change the port in `AirflowServiceManager`

### "Services Start But Can't Connect"

**Solution**:
1. Wait a few more seconds (API server needs time to initialize)
2. Click "Check Connection" button
3. Check console output for errors

### Services Won't Stop

**Solution**:
- Services are force-killed after 5 seconds if graceful shutdown fails
- Check Task Manager (Windows) or `ps aux` (Linux) for orphaned processes

## Integration with Existing Features

### Workflow Integration

- Pipelines can be triggered from Airflow UI
- Airflow DAGs use the unified pipeline runner
- All runs are tracked in the desktop UI's event history

### Logging Integration

- Airflow logs are separate from platform logs
- Platform logs available in "Logs" tab
- Airflow logs available in Airflow UI

## Future Enhancements

Potential improvements:

1. **Auto-start on App Launch**: Option to auto-start Airflow services
2. **Service Health Dashboard**: Visual dashboard showing service health
3. **DAG Builder UI**: Visual DAG creation tool
4. **Multi-Environment Support**: Switch between dev/staging/prod Airflow instances
5. **Windows Service**: Run Airflow as Windows service for auto-start

## Code Structure

```
src/ui/
├── airflow_service.py      # Service manager
├── main_window.py          # Updated UI with Airflow integration
├── workflow_graph.py       # Workflow visualization
├── theme.py                # Theme management
└── logging_handler.py     # UI logging
```

## Summary

The desktop application now provides a **complete Airflow experience** without requiring:
- ❌ Separate browser windows
- ❌ Manual terminal commands
- ❌ External service management

Everything runs **within one unified desktop application** with full control over Airflow services.

---

**Status**: ✅ Fully Implemented  
**Version**: 5.0  
**Last Updated**: 2024

