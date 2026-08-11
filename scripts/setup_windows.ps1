# ORBIT Windows setup script.
# Run from an elevated or normal PowerShell prompt in the project root:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "== ORBIT Windows setup ==" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "Python was not found on PATH. Install Python 3.10-3.12 from https://python.org and re-run this script." -ForegroundColor Red
    exit 1
}
$pyVersion = & python --version
Write-Host "Found $pyVersion"

# 2. Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment (.venv)..."
    python -m venv .venv
}

# 3. Activate and install dependencies
Write-Host "Installing dependencies (this can take a few minutes)..."
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements\base.txt
pip install -r requirements\windows.txt

# 4. Playwright browser (for browser control tool)
Write-Host "Installing Playwright's Chromium browser..."
python -m playwright install chromium

# 5. .env file
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env created from .env.example — edit it to add API keys if you want cloud LLM reasoning." -ForegroundColor Yellow
}

# 6. Data directories
python -c "from orbit.config import settings; print('Data directory ready at', settings.data_dir)"

Write-Host ""
Write-Host "== Setup complete ==" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Download an ASR model:   python scripts\download_asr_model.py --size small"
Write-Host "  2. Try text mode:           python main.py --text"
Write-Host "  3. Run the real voice loop: python main.py --voice"
Write-Host "See README.md for full details, required Windows permissions, and troubleshooting."
