#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[migrate] Applying database migrations"
# Try alembic first (if configured), fall back to SQL migrations
if [ -f "$ROOT_DIR/alembic.ini" ]; then
  PYTHONPATH="$ROOT_DIR/src" alembic upgrade head || \
    python "$ROOT_DIR/scripts/run_sql_migrations.py"
else
  # No alembic config, use SQL migrations directly
  python "$ROOT_DIR/scripts/run_sql_migrations.py"
fi

