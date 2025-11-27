# Troubleshooting API Startup Issues

## Symptoms
- API container starts but health checks fail
- `curl` returns "Connection reset by peer" or "Empty reply from server"
- API container shows as "unhealthy" in `docker compose ps`

## Common Causes

### 1. Missing Environment Variables
The API requires `DB_URL` and `SCRAPER_SECRET_KEY` to start.

**Check:**
```bash
sudo docker compose exec api env | grep -E '(DB_|SCRAPER_)'
```

**Fix:**
Create a `.env` file in the project root:
```bash
cat > .env << 'EOF'
DB_URL=postgresql://scraper:scraper123@postgres:5432/scraperdb
DB_HOST=postgres
DB_USER=scraper
DB_PASSWORD=scraper123
DB_NAME=scraperdb
SCRAPER_SECRET_KEY=your-secret-key-here
EOF
```

Or ensure these are set in `docker-compose.yml` environment section (defaults are provided).

### 2. Database Connection Issues
The API validates database connectivity on startup.

**Check:**
```bash
# Test DB connection from API container
sudo docker compose exec api python -c "from src.common.db import get_conn; conn = get_conn(); print('Connected:', conn.status)"
```

**Fix:**
- Ensure postgres container is healthy: `sudo docker compose ps postgres`
- Check postgres logs: `sudo docker compose logs postgres`
- Verify DB credentials match between API and postgres service

### 3. Schema Version Mismatch
The API checks that the database schema version matches the expected version.

**Check API logs:**
```bash
sudo docker compose logs api | grep -i "schema\|version\|migration"
```

**Fix:**
Run migrations:
```bash
sudo docker compose run --rm \
  -e DB_HOST=postgres \
  -e DB_USER=scraper \
  -e DB_PASSWORD=scraper123 \
  -e DB_NAME=scraperdb \
  api sh -c "chmod +x /app/scripts/migrate.sh && /app/scripts/migrate.sh"
```

### 4. API Container Crashing
The container may be crashing immediately on startup.

**Check:**
```bash
# Check if container is running
sudo docker compose ps api

# Check exit code
sudo docker compose ps api | grep -i exit

# View full logs
sudo docker compose logs api --tail=100
```

**Common errors in logs:**
- `RuntimeError: Missing required environment variables` → Fix env vars
- `RuntimeError: Database schema_version table missing` → Run migrations
- `RuntimeError: DB schema version X does not match expected Y` → Run migrations
- `psycopg2.OperationalError` → Database connection issue

### 5. Port Already in Use
Another process may be using port 8000.

**Check:**
```bash
sudo lsof -i :8000
# or
sudo netstat -tulpn | grep 8000
```

**Fix:**
- Stop the conflicting process
- Or change the port in `docker-compose.yml`

## Quick Diagnostic Commands

```bash
# 1. Check container status
sudo docker compose ps

# 2. Check API logs
sudo docker compose logs api --tail=50

# 3. Check environment variables
sudo docker compose exec api env | grep -E '(DB_|SCRAPER_)'

# 4. Test database connection
sudo docker compose exec postgres psql -U scraper -d scraperdb -c "SELECT version();"

# 5. Check if API process is running inside container
sudo docker compose exec api ps aux | grep uvicorn

# 6. Test API from inside container
sudo docker compose exec api curl -f http://localhost:8000/health

# 7. Check for Python errors
sudo docker compose exec api python -c "import src.api.app; print('Import OK')"
```

## Step-by-Step Recovery

1. **Stop all services:**
   ```bash
   sudo docker compose down
   ```

2. **Verify database is accessible:**
   ```bash
   sudo docker compose up -d postgres redis
   sleep 5
   sudo docker compose exec postgres psql -U scraper -d scraperdb -c "SELECT 1;"
   ```

3. **Run migrations if needed:**
   ```bash
   sudo docker compose run --rm \
     -e DB_HOST=postgres \
     -e DB_USER=scraper \
     -e DB_PASSWORD=scraper123 \
     -e DB_NAME=scraperdb \
     api sh -c "chmod +x /app/scripts/migrate.sh && /app/scripts/migrate.sh"
   ```

4. **Start API with verbose logging:**
   ```bash
   sudo docker compose up api
   # Watch for errors, then Ctrl+C
   ```

5. **Start in background and check:**
   ```bash
   sudo docker compose up -d api
   sleep 10
   curl -v http://localhost:8000/health
   ```

## Still Not Working?

1. Check the full API startup sequence:
   ```bash
   sudo docker compose logs api | grep -A 10 -B 10 -i "error\|exception\|traceback"
   ```

2. Verify the code was pulled correctly:
   ```bash
   git log --oneline -5
   git status
   ```

3. Rebuild from scratch:
   ```bash
   sudo docker compose build --no-cache api
   sudo docker compose up -d api
   ```

4. Check system resources:
   ```bash
   free -h
   df -h
   ```

