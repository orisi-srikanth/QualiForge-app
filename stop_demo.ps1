# =============================================================================
# QualityMind Demo Shutdown Script (Windows, No Docker)
# =============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  STOPPING QUALITYMIND SERVICES (NATIVE RUNTIMES)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Stop recorded PIDs if file exists
if (Test-Path "$ScriptDir/.demo_pids") {
    $pidsToKill = Get-Content "$ScriptDir/.demo_pids"
    foreach ($p in $pidsToKill) {
        if ($p -match '^\d+$') {
            try {
                Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue
                Write-Host "  Stopped launcher process (PID: $p)" -ForegroundColor Gray
            } catch {}
        }
    }
    Remove-Item "$ScriptDir/.demo_pids" -Force -ErrorAction SilentlyContinue
}

# 2. Kill any processes still listening on port 8000 (Backend)
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($port8000) {
    foreach ($pid8000 in $port8000) {
        if ($pid8000 -gt 4) {
            try {
                Stop-Process -Id $pid8000 -Force -ErrorAction SilentlyContinue
                Write-Host "  Terminated Backend listener (PID: $pid8000) on port 8000." -ForegroundColor Green
            } catch {}
        }
    }
} else {
    Write-Host "  Port 8000 is free." -ForegroundColor Gray
}

# 3. Kill any processes still listening on port 5173 (Frontend Vite)
$port5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($port5173) {
    foreach ($pid5173 in $port5173) {
        if ($pid5173 -gt 4) {
            try {
                Stop-Process -Id $pid5173 -Force -ErrorAction SilentlyContinue
                Write-Host "  Terminated Frontend listener (PID: $pid5173) on port 5173." -ForegroundColor Green
            } catch {}
        }
    }
} else {
    Write-Host "  Port 5173 is free." -ForegroundColor Gray
}

# 4. Final verification
Start-Sleep -Seconds 1
$check8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$check5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

if (-not $check8000 -and -not $check5173) {
    Write-Host "`nAll QualityMind services stopped successfully. Ports 8000 and 5173 are clean." -ForegroundColor Green
} else {
    Write-Host "`nWarning: Some processes may still be running." -ForegroundColor Yellow
}
