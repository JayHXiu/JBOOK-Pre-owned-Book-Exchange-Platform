#!/usr/bin/env bash
# Railway 启动：迁移 →（按需）同步业务数据 → Gunicorn
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[1/3] migrate"
python manage.py migrate --noinput

if [ "${JBOOK_BOOTSTRAP:-1}" = "1" ]; then
  echo "[2/3] bootstrap_jbook (PG BX 表或 CSV)"
  python manage.py bootstrap_jbook --source auto || true
else
  echo "[2/3] skip bootstrap (JBOOK_BOOTSTRAP=0)"
fi

echo "[3/3] gunicorn"
exec gunicorn booktrade.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120
