# Runs the real ORBIT voice loop (Windows only).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_orbit.ps1

$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Run scripts\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}
& .\.venv\Scripts\Activate.ps1
python main.py --voice
