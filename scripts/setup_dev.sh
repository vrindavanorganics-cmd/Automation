#!/usr/bin/env bash
# Sets up ORBIT for local development/testing on Linux/macOS (or this
# browser Claude Code workspace). Does NOT install Windows-only computer
# control / voice dependencies — see requirements/windows.txt and
# scripts/setup_windows.ps1 for the real Windows install.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements/dev.txt -q

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ".env created from .env.example"
fi

echo "Setup complete. Try:"
echo "  source .venv/bin/activate"
echo "  python main.py --text"
echo "  pytest -q"
