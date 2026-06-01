@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PYTHONUTF8=1"
set "USE_SQLITE=True"
set "PY=venv\Scripts\python.exe"

echo ========================================
echo   JBOOK backend setup check
echo ========================================

if not exist "%PY%" (
    echo [WARN] venv not found. Run scripts\run.bat first.
    exit /b 1
)

call "%PY%" manage.py check
if errorlevel 1 exit /b 1

call "%PY%" manage.py makemigrations --check --dry-run >nul 2>&1
if errorlevel 1 (
    echo [INFO] Pending model changes. Run run.bat to migrate.
) else (
    echo [OK] Migrations up to date.
)

echo [OK] Django project is ready.
exit /b 0
