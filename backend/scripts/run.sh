#!/usr/bin/env bash
# JBOOK Django launcher (Linux/macOS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

export PYTHONUTF8=1
export USE_SQLITE=True

PY="${PROJECT_DIR}/venv/bin/python"
PIP="${PROJECT_DIR}/venv/bin/pip"

if [[ ! -x "$PY" ]]; then
  echo "[1/5] Creating virtual environment..."
  python3 -m venv venv
fi

echo "[2/5] Installing dependencies..."
"$PIP" install -r requirements.txt -q

echo "[3/5] Running migrations..."
"$PY" manage.py makemigrations --noinput 2>/dev/null || true
"$PY" manage.py migrate --noinput

if [[ ! -f db.sqlite3 ]]; then
  echo "[4/5] Downloading Book-Crossing & seeding..."
  "$PY" ../data/book_crossing/download.py
  "$PY" manage.py seed_demo --force
else
  echo "[4/5] DB exists. Run: manage.py seed_demo --force to reload data"
fi

echo
echo "========================================"
echo " JBOOK  http://127.0.0.1:8000/"
echo " admin / admin123"
echo " seller1 / 123456"
echo " buyer1 / 123456"
echo "========================================"
echo

echo "[5/5] Starting server..."
"$PY" manage.py runserver 127.0.0.1:8000
