#!/usr/bin/env bash
# Quick diagnostic script for API startup issues

set -euo pipefail

echo "=== API Diagnostic Script ==="
echo ""

echo "1. Checking container status..."
sudo docker compose ps api
echo ""

echo "2. Checking API logs (last 50 lines)..."
sudo docker compose logs api --tail=50
echo ""

echo "3. Checking if API process is running inside container..."
sudo docker compose exec api ps aux 2>/dev/null || echo "Container may not be running or accessible"
echo ""

echo "4. Checking environment variables..."
sudo docker compose exec api env 2>/dev/null | grep -E '(DB_|SCRAPER_)' || echo "Cannot access container environment"
echo ""

echo "5. Testing database connection from API container..."
sudo docker compose exec api python -c "
try:
    from src.common.db import get_conn
    conn = get_conn()
    print('✓ Database connection: OK')
    print(f'  Connection status: {conn.status}')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
" 2>/dev/null || echo "Cannot test database connection"
echo ""

echo "6. Checking schema version..."
sudo docker compose exec api python -c "
try:
    from src.db.schema_version import schema_version_table_exists, get_schema_version
    from src.api.constants import EXPECTED_SCHEMA_VERSION
    if schema_version_table_exists():
        ver = get_schema_version()
        print(f'✓ Schema version table exists')
        print(f'  Current version: {ver}')
        print(f'  Expected version: {EXPECTED_SCHEMA_VERSION}')
        if ver != EXPECTED_SCHEMA_VERSION:
            print(f'  ⚠️  VERSION MISMATCH - Run migrations!')
        else:
            print(f'  ✓ Version matches')
    else:
        print('✗ Schema version table missing - Run migrations!')
except Exception as e:
    print(f'✗ Error checking schema: {e}')
" 2>/dev/null || echo "Cannot check schema version"
echo ""

echo "7. Testing API import..."
sudo docker compose exec api python -c "
try:
    import src.api.app
    print('✓ API module imports successfully')
except Exception as e:
    print(f'✗ API import failed: {e}')
    import traceback
    traceback.print_exc()
" 2>/dev/null || echo "Cannot test API import"
echo ""

echo "8. Checking if port 8000 is accessible from inside container..."
sudo docker compose exec api curl -f http://localhost:8000/health 2>/dev/null && echo "✓ Health endpoint responds" || echo "✗ Health endpoint not responding"
echo ""

echo "=== Diagnostic Complete ==="
echo ""
echo "Common fixes:"
echo "  - If schema version mismatch: Run migrations"
echo "  - If missing env vars: Check .env file or docker-compose.yml"
echo "  - If import errors: Check API logs above for Python errors"

