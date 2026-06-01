@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
if errorlevel 1 (
    echo [ERROR] Cannot enter backend directory.
    exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "USE_SQLITE=True"
set "PY=venv\Scripts\python.exe"
set "PIP=venv\Scripts\pip.exe"

if not exist "%PY%" (
    echo [1/5] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Install Python 3.10+ first.
        exit /b 1
    )
)

echo [2/5] Installing dependencies...
call "%PIP%" install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install failed.
    exit /b 1
)

echo [3/5] Running migrations...
call "%PY%" manage.py makemigrations --noinput 2>nul
call "%PY%" manage.py migrate --noinput
if errorlevel 1 (
    echo [ERROR] migrate failed.
    exit /b 1
)

if not exist "db.sqlite3" (
    echo [4/5] Downloading Book-Crossing and seeding...
    call "%PY%" ..\..\data\book_crossing\download.py
    call "%PY%" manage.py seed_demo --force
) else (
    echo [4/5] DB exists. Run: manage.py seed_demo --force  to reload Book-Crossing
)

echo.
echo ========================================
echo  JBOOK
echo  http://127.0.0.1:8000/
echo  admin / admin123
echo  seller1 / 123456
echo  buyer1 / 123456
echo ========================================
echo.

echo [5/5] Starting server...
call "%PY%" manage.py runserver 127.0.0.1:8000

endlocal
