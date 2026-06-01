# JBOOK backend launcher (PowerShell)
# Use ASCII log messages to avoid console encoding garbling on Windows.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:USE_SQLITE = "True"

$py = Join-Path $PWD "venv\Scripts\python.exe"
$pip = Join-Path $PWD "venv\Scripts\pip.exe"

if (-not (Test-Path $py)) {
    Write-Host "[1/5] Creating virtual environment..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
}

Write-Host "[2/5] Installing dependencies..."
& $pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "[3/5] Running migrations..."
& $py manage.py makemigrations --noinput 2>$null
& $py manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "migrate failed" }

if (-not (Test-Path "db.sqlite3")) {
    Write-Host "[4/5] Downloading Book-Crossing & seeding..."
    & $py ..\..\data\book_crossing\download.py
    & $py manage.py seed_demo --force
} else {
    Write-Host "[4/5] Book-Crossing seed check (use seed_demo --force to reload)..."
}

Write-Host ""
Write-Host "========================================"
Write-Host " JBOOK"
Write-Host " http://127.0.0.1:8000/"
Write-Host " admin / admin123"
Write-Host " seller1 / 123456"
Write-Host " buyer1 / 123456"
Write-Host "========================================"
Write-Host ""

Write-Host "[5/5] Starting server..."
& $py manage.py runserver 127.0.0.1:8000
