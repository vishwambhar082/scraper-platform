#!/usr/bin/env bash
# === CODE-ONLY DEPLOY: no DB changes ===
# Deploys code changes without running migrations

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Step 1: Resolve Git Divergence ==="
# Configure git to handle divergent branches (merge strategy)
if ! git config pull.rebase > /dev/null 2>&1; then
    echo "Configuring git pull strategy (merge)..."
    git config pull.rebase false
fi

echo "Pulling latest code from origin/main..."
# Try with explicit merge strategy first
if ! git pull --no-rebase origin main 2>/dev/null; then
    echo ""
    echo "⚠️  Git pull failed due to divergent branches."
    echo "Attempting to reset to origin/main (this discards local changes)..."
    git fetch origin
    if git reset --hard origin/main; then
        echo "✓ Successfully reset to origin/main"
    else
        echo "✗ Failed to reset. Please resolve manually:"
        echo "  git fetch origin"
        echo "  git reset --hard origin/main"
        exit 1
    fi
fi

echo ""
echo "=== Step 2: Rebuild API + Frontend Images ==="
# Rebuild API + frontend images (DB volume untouched)
sudo docker compose build api frontend

echo ""
echo "=== Step 3: Restart API + Frontend ==="
# Restart API + frontend with new images
sudo docker compose up -d api frontend

echo ""
echo "=== Step 4: Check Status & Logs ==="
sudo docker compose ps
echo ""
echo "=== Recent API Logs (last 50 lines) ==="
sudo docker compose logs api --tail=50

echo ""
echo "=== Step 5: Health Check ==="
# Wait a moment for API to start
echo "Waiting 10 seconds for API to start..."
sleep 10

# Try health endpoints with retries
MAX_RETRIES=3
RETRY_COUNT=0
HEALTH_CHECK_PASSED=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✓ API health check passed at /api/health"
        HEALTH_CHECK_PASSED=true
        break
    elif curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API health check passed at /health"
        HEALTH_CHECK_PASSED=true
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⏳ Health check failed, retrying in 5 seconds... ($RETRY_COUNT/$MAX_RETRIES)"
            sleep 5
        fi
    fi
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo ""
    echo "✗ API health check failed after $MAX_RETRIES attempts."
    echo ""
    echo "=== Troubleshooting ==="
    echo "1. Check API container status:"
    echo "   sudo docker compose ps api"
    echo ""
    echo "2. Check API logs for errors:"
    echo "   sudo docker compose logs api --tail=100"
    echo ""
    echo "3. Check if API container is running:"
    echo "   sudo docker compose exec api ps aux"
    echo ""
    echo "4. Verify environment variables:"
    echo "   sudo docker compose exec api env | grep -E '(DB_|SCRAPER_)'"
    echo ""
    echo "5. Test database connectivity from API container:"
    echo "   sudo docker compose exec api python -c \"from src.common.db import get_conn; get_conn()\""
    echo ""
    echo "Common issues:"
    echo "  - Missing DB_URL or SCRAPER_SECRET_KEY environment variables"
    echo "  - Database connection issues"
    echo "  - Schema version mismatch (may need to run migrations)"
    echo "  - API crashing on startup (check logs above)"
    exit 1
fi

echo ""
echo "=== Deployment Complete ==="
echo "✓ API is healthy and responding"
echo "✓ Frontend has been rebuilt and restarted"

