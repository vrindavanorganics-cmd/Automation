# Runs ORBIT in text mode (no mic/hotkey needed) - useful to sanity-check
# a fresh install before trying real voice control.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_text_mode.ps1

$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Run scripts\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}
& .\.venv\Scripts\Activate.ps1
python main.py --text
