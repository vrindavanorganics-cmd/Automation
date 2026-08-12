# Lists the real Chrome profiles ORBIT can see on this PC.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\list_chrome_profiles.ps1

$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Run scripts\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}
& .\.venv\Scripts\Activate.ps1
python scripts\list_chrome_profiles.py
