# Running Scraper Platform with Docker

This guide explains how to run the Scraper Platform using Docker, which resolves the Windows compatibility issues with Airflow.

## Prerequisites

1. Docker Desktop installed on your system
2. Git (if cloning the repository)

## Quick Start

1. **Build and start the services:**
   ```bash
   docker-compose up -d
   ```

2. **Access the Airflow UI:**
   Open your browser and go to http://localhost:8080
   - Username: admin
   - Password: admin

3. **Access the Desktop UI:**
   ```bash
   docker-compose exec airflow-webserver python run_ui.py
   ```

## Detailed Instructions

### Building the Images

The first time you run the platform, Docker will build the images:

```bash
docker-compose build
```

### Starting Services

To start all services in the background:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database for Airflow
- Airflow webserver
- Airflow scheduler

### Stopping Services

To stop all services:

```bash
docker-compose down
```

To stop services and remove volumes (including database data):

```bash
docker-compose down -v
```

### Viewing Logs

To view logs for all services:

```bash
docker-compose logs -f
```

To view logs for a specific service:

```bash
docker-compose logs -f airflow-webserver
```

## Configuration

### Environment Variables

The docker-compose.yml file sets the necessary environment variables for Airflow. You can modify these in the file if needed.

### Volume Mounts

The following directories are mounted as volumes:
- `./dags` - Airflow DAGs
- `./logs` - Airflow logs
- `./config` - Configuration files

This allows you to modify these files on your host system and have the changes reflected in the containers.

## Troubleshooting

### Port Already in Use

If port 8080 is already in use on your system, modify the port mapping in docker-compose.yml:

```yaml
ports:
  - "8081:8080"  # Change host port to 8081
```

### Database Issues

If you encounter database issues, try resetting the database:

```bash
docker-compose down -v
docker-compose up -d
```

### Rebuilding Images

If you make changes to the Dockerfile or requirements, rebuild the images:

```bash
docker-compose build --no-cache
```

## Using the Platform

Once the services are running:

1. Access the Airflow UI at http://localhost:8080
2. Log in with username/password: admin/admin
3. Enable and trigger the desired scraper DAGs
4. Monitor execution in the Airflow UI

Alternatively, you can run scrapers directly without Airflow using the desktop UI or command line:

```bash
docker-compose exec airflow-webserver python -m src.entrypoints.run_pipeline --source alfabeta --environment dev
```