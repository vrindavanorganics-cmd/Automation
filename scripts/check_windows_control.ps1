# Runs the Windows computer-control diagnostic using the project's virtual
# environment (not your system Python), so it actually checks the packages
# that were installed by setup_windows.ps1.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\check_windows_control.ps1
#        powershell -ExecutionPolicy Bypass -File scripts\check_windows_control.ps1 -- --launch-test

$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Run scripts\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}
& .\.venv\Scripts\Activate.ps1
python scripts\check_windows_control.py @args
