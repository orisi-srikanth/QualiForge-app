# =============================================================================
# QualityMind Single-Command Windows Demo Launcher (No Docker Required)
# =============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  QUALITYMIND INDUSTRIAL QUALITY INTELLIGENCE PLATFORM (LOCAL RUNNER)" -ForegroundColor Cyan
Write-Host "  Native Environment: Python FastAPI + React Vite (Zero Containers)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Check Python
Write-Host "`n[Step 1/6] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVer = python --version 2>&1
    Write-Host "  Found: $pythonVer" -ForegroundColor Green
} catch {
    Write-Error "Python is not found in PATH. Please install Python 3.11+."
    exit 1
}

# 2. Check Node & npm
Write-Host "`n[Step 2/6] Checking Node.js and npm..." -ForegroundColor Yellow
try {
    $nodeVer = node --version 2>&1
    $npmVer = npm --version 2>&1
    Write-Host "  Found Node: $nodeVer | npm: $npmVer" -ForegroundColor Green
} catch {
    Write-Error "Node.js/npm not found in PATH. Please install Node.js 20+."
    exit 1
}

# 3. Check Database (PostgreSQL vs SQLite)
Write-Host "`n[Step 3/6] Detecting Database Engine..." -ForegroundColor Yellow
$pgCmd = Get-Command psql -ErrorAction SilentlyContinue
if ($pgCmd) {
    Write-Host "  PostgreSQL CLI detected: $($pgCmd.Source)" -ForegroundColor Green
} else {
    Write-Host "  PostgreSQL not detected locally. Operating in local SQLite fallback mode." -ForegroundColor Magenta
    Write-Host "  Active Database: sqlite:///./backend/data/quality_system.db" -ForegroundColor Magenta
}

# 4. Check Virtual Environment & Install Dependencies if needed
Write-Host "`n[Step 4/6] Checking Python environment & migrations..." -ForegroundColor Yellow
$env:PYTHONPATH = $ScriptDir

# Run migrations
Write-Host "  Applying database migrations (alembic upgrade head)..." -ForegroundColor Gray
python -m alembic upgrade head

# Check if database needs seeding
$needsSeed = python -c "from backend.app.db.session import engine; from sqlalchemy import text; conn=engine.connect(); cnt=conn.execute(text('SELECT COUNT(*) FROM users')).scalar(); conn.close(); print(cnt == 0)" 2>&1
if ($needsSeed -match "True") {
    Write-Host "  Database is empty. Seeding anchor scenario and manufacturing batches..." -ForegroundColor Yellow
    python -m backend.app.db.seed
    Write-Host "  Database seeded successfully." -ForegroundColor Green
} else {
    Write-Host "  Database already seeded with production batches and incidents." -ForegroundColor Green
}

# 5. Start Backend and Frontend Servers
Write-Host "`n[Step 5/6] Launching Backend & Frontend services in separate windows..." -ForegroundColor Yellow

# Clean up any existing listeners on 8000 and 5173
$oldPort8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($oldPort8000) {
    foreach ($p in $oldPort8000) {
        if ($p -gt 4) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
    }
}
$oldPort5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($oldPort5173) {
    foreach ($p in $oldPort5173) {
        if ($p -gt 4) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
    }
}

# Resolve PowerShell executable
$psExe = if (Get-Command powershell -ErrorAction SilentlyContinue) { "powershell" } elseif (Test-Path "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe") { "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" } else { "powershell.exe" }

# Start Backend
$backendProcess = Start-Process $psExe -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; `$env:PYTHONPATH='$ScriptDir'; python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000" -PassThru
Write-Host "  Backend started (PID: $($backendProcess.Id)) at http://localhost:8000" -ForegroundColor Green

# Start Frontend
$frontendProcess = Start-Process $psExe -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir/frontend'; npm run dev" -PassThru
Write-Host "  Frontend started (PID: $($frontendProcess.Id)) at http://localhost:5173" -ForegroundColor Green

# Save PIDs to .pids file for clean shutdown
Set-Content -Path "$ScriptDir/.demo_pids" -Value "$($backendProcess.Id)`n$($frontendProcess.Id)"

# 6. Wait for Health Check & Launch Browser
Write-Host "`n[Step 6/6] Waiting for services to become healthy..." -ForegroundColor Yellow
$healthy = $false
$retries = 30
while (-not $healthy -and $retries -gt 0) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($res.status -match "HEALTHY|healthy") {
            $healthy = $true
        }
    } catch {
        # Waiting for backend
    }
    $retries--
}

if ($healthy) {
    Write-Host "  Backend health check verified: status=healthy" -ForegroundColor Green
} else {
    Write-Host "  Warning: Backend took longer than expected to report healthy." -ForegroundColor Yellow
}

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "  ALL SYSTEMS RUNNING NATIVELY (ZERO DOCKER OVERHEAD)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Application UI  : http://localhost:5173" -ForegroundColor Green
Write-Host "  Swagger UI Docs : http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  ReDoc Docs      : http://localhost:8000/redoc" -ForegroundColor Green
Write-Host "  Health Endpoint : http://localhost:8000/health" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Opening endpoints in default browser..." -ForegroundColor Gray

Start-Process "http://localhost:5173" -ErrorAction SilentlyContinue
Start-Process "http://localhost:8000/docs" -ErrorAction SilentlyContinue
Start-Process "http://localhost:8000/redoc" -ErrorAction SilentlyContinue

Write-Host "`nTo stop the demo at any time, run: .\stop_demo.ps1" -ForegroundColor Yellow
