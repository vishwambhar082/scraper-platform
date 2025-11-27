#!/usr/bin/env bash
# === CODE + DB SCHEMA CHANGES DEPLOY ===
# Safe deployment script that handles common issues

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Step 1: Resolve Git Divergence ==="
# Configure git to handle divergent branches (merge strategy)
if ! git config pull.rebase > /dev/null 2>&1; then
    echo "Configuring git pull strategy (merge)..."
    git config pull.rebase false
fi

echo "Pulling latest code from origin/main..."
git pull origin main || {
    echo "WARNING: Git pull had issues. If branches have diverged, you may need to:"
    echo "  git fetch origin"
    echo "  git reset --hard origin/main  # WARNING: This discards local changes"
    echo "Or manually resolve conflicts and retry."
    exit 1
}

echo ""
echo "=== Step 2: Run Database Migrations ==="
# Run migrations safely against existing DB (no data loss if migrations are additive)
sudo docker compose run --rm \
  -e DB_HOST=postgres \
  -e DB_USER=scraper \
  -e DB_PASSWORD=scraper123 \
  -e DB_NAME=scraperdb \
  api sh -c "chmod +x /app/scripts/migrate.sh && /app/scripts/migrate.sh"

echo ""
echo "=== Step 3: Rebuild API Image ==="
# Rebuild API image if code/models/endpoints changed
sudo docker compose build api

echo ""
echo "=== Step 4: Restart API ==="
# Restart API (DB volume is reused as-is)
sudo docker compose up -d api

echo ""
echo "=== Step 5: Check Status & Logs ==="
sudo docker compose ps
echo ""
echo "=== Recent API Logs ==="
sudo docker compose logs api | tail -n 40

echo ""
echo "=== Step 6: Health Check ==="
# Wait a moment for API to start
sleep 5

# Try health endpoints
if curl -f -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✓ API health check passed at /api/health"
elif curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ API health check passed at /health"
else
    echo "✗ API health check failed. Check logs above for errors."
    echo "Common issues:"
    echo "  - Missing DB_URL or SCRAPER_SECRET_KEY environment variables"
    echo "  - Database connection issues"
    echo "  - Schema version mismatch"
    exit 1
fi

echo ""
echo "=== Deployment Complete ==="
