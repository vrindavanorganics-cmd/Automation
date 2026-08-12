# Pulls the latest ORBIT code, updates installed packages, and makes sure
# your .env has the settings the latest code expects (e.g. a default Chrome
# profile) -- all in one paste, no manual file editing.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\update_orbit.ps1

$ErrorActionPreference = "Stop"

Write-Host "Pulling latest ORBIT code..." -ForegroundColor Cyan
git pull origin claude/orbit-ai-desktop-agent-s6hs6c

if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Run scripts\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}
& .\.venv\Scripts\Activate.ps1

Write-Host "Updating installed packages..." -ForegroundColor Cyan
pip install -q -r requirements\base.txt
if (Test-Path "requirements\windows.txt") {
    pip install -q -r requirements\windows.txt
}

if (-not (Test-Path ".env")) {
    Write-Host "No .env found -- copying from .env.example." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

$envContent = Get-Content ".env" -Raw
if ($envContent -notmatch "(?m)^ORBIT_CHROME_PROFILE=.+") {
    Write-Host "Setting default Chrome profile to 'Vrindavan Organics' in .env..." -ForegroundColor Cyan
    if ($envContent -match "(?m)^ORBIT_CHROME_PROFILE=") {
        $envContent = $envContent -replace "(?m)^ORBIT_CHROME_PROFILE=.*$", "ORBIT_CHROME_PROFILE=Vrindavan Organics"
    } else {
        $envContent += "`nORBIT_CHROME_PROFILE=Vrindavan Organics`n"
    }
    Set-Content ".env" $envContent -NoNewline
}

Write-Host "Update complete. Run scripts\run_orbit.ps1 to start ORBIT." -ForegroundColor Green
