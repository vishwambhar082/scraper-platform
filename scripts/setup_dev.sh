#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python -m venv .venv || true
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  # Windows Git Bash
  # shellcheck disable=SC1091
  source .venv/Scripts/activate
fi

python -m pip install --upgrade pip
python -m pip install -r requirements.txt || true

mkdir -p sessions/cookies sessions/logs output/alfabeta/daily input logs

echo "Dev setup complete. Activate venv with 'source .venv/bin/activate' (linux/mac) or '.\\.venv\\Scripts\\activate' (windows)."

