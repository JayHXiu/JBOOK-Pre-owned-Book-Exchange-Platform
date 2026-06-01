#!/usr/bin/env bash
# JBOOK Django project check (Linux/macOS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

export USE_SQLITE=True
PY="${PROJECT_DIR}/venv/bin/python"

echo "========================================"
echo "  JBOOK backend setup check"
echo "========================================"

if [[ ! -x "$PY" ]]; then
  echo "[WARN] venv not found. Run scripts/run.sh first."
  exit 1
fi

"$PY" manage.py check
"$PY" manage.py makemigrations --check --dry-run >/dev/null 2>&1 || \
  echo "[INFO] Pending model changes. Run migrate."

echo "[OK] Django project is ready."
