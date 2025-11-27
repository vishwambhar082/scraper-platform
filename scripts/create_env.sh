#!/usr/bin/env bash
# Create .env file with secure defaults
# Usage: ./scripts/create_env.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    echo "Backup will be created at .env.backup"
    cp .env .env.backup
fi

# Generate secure secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "CHANGE-ME-$(date +%s)")

cat > .env << EOF
# Database Configuration
DB_URL=postgresql://scraper:scraper123@postgres:5432/scraperdb
DB_HOST=postgres
DB_USER=scraper
DB_PASSWORD=scraper123
DB_NAME=scraperdb

# API Security
SCRAPER_SECRET_KEY=${SECRET_KEY}

# PostgreSQL (used by docker-compose)
POSTGRES_USER=scraper
POSTGRES_PASSWORD=scraper123
POSTGRES_DB=scraperdb

# Optional: Logging
LOG_LEVEL=INFO

# Python Path
PYTHONPATH=/app
EOF

chmod 600 .env

echo "✅ .env file created successfully!"
echo ""
echo "SCRAPER_SECRET_KEY: ${SECRET_KEY}"
echo ""
echo "⚠️  IMPORTANT for production:"
echo "   - Change POSTGRES_PASSWORD to a secure value"
echo "   - Secure the .env file permissions (already set to 600)"
echo ""
echo "File location: $(pwd)/.env"
