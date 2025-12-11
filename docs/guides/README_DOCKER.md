# Scraper Platform - Docker Setup

This document provides instructions for running the Scraper Platform using Docker, which resolves the Windows compatibility issues with Airflow.

## Why Docker?

Airflow 3.x has limited support on Windows and requires either WSL2 or Docker for proper operation. Docker provides a consistent environment that works across all platforms.

## Prerequisites

1. Docker Desktop for Windows (https://www.docker.com/products/docker-desktop)
2. Git (optional, if cloning the repository)

## Quick Start with Docker

1. **Install Docker Desktop** - Download and install from https://www.docker.com/products/docker-desktop

2. **Start Docker Desktop** - Make sure the Docker daemon is running

3. **Build and start the services:**
   ```bash
   docker-compose up -d
   ```

4. **Access the Airflow UI:**
   Open your browser and go to http://localhost:8080
   - Username: admin
   - Password: admin

## Alternative: Run Without Airflow

If you prefer not to use Docker or Airflow, you can run the scrapers directly:

1. **Using the batch file (Windows):**
   Double-click `run_without_airflow.bat`

2. **Using the command line:**
   ```bash
   # Activate virtual environment
   .venv\Scripts\activate
   
   # Run a scraper
   python -m src.entrypoints.run_pipeline --source alfabeta --environment dev
   ```

3. **Using the Desktop UI:**
   ```bash
   python run_ui.py
   ```
   Then navigate to the "Jobs" tab to run scrapers.

## Directory Structure

```
scraper-platform/
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Service definitions
├── docker-init.sh          # Initialization script
├── .dockerignore           # Files to exclude from Docker build
├── DOCKER_INSTRUCTIONS.md  # Detailed Docker instructions
├── RUN_WITHOUT_AIRFLOW.md  # Instructions for direct execution
├── run_without_airflow.bat # Windows batch file for direct execution
└── README_DOCKER.md        # This file
```

## Docker Services

The docker-compose.yml defines the following services:

1. **postgres** - PostgreSQL database for Airflow metadata
2. **airflow-webserver** - Airflow web interface
3. **airflow-scheduler** - Airflow job scheduler

## Configuration

### Environment Variables

The docker-compose.yml file sets the necessary environment variables for Airflow. You can modify these in the file if needed.

### Volume Mounts

The following directories are mounted as volumes for data persistence:
- PostgreSQL data
- Airflow DAGs
- Airflow logs
- Configuration files

## Troubleshooting

### Docker Daemon Not Running

Make sure Docker Desktop is installed and running. You should see the Docker icon in your system tray.

### Port Conflicts

If port 8080 is already in use, modify the port mapping in docker-compose.yml:
```yaml
ports:
  - "8081:8080"  # Change to port 8081
```

### Database Issues

If you encounter database issues, reset the database:
```bash
docker-compose down -v
docker-compose up -d
```

## Next Steps

1. **Explore the Airflow UI** - Access http://localhost:8080 to see available DAGs
2. **Enable a DAG** - Toggle the switch to enable a scraper DAG
3. **Trigger a DAG** - Click the "Play" button to run a scraper
4. **Monitor execution** - Watch the progress in the Airflow UI

## Support

For issues with the Docker setup, refer to:
- DOCKER_INSTRUCTIONS.md for detailed Docker usage
- RUN_WITHOUT_AIRFLOW.md for direct execution options
- The main documentation in consolidated-docs/