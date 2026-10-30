#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "            ECO-SHIELD Production Deployment Launcher (Linux/Mac)     "
echo "======================================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/3] Building frontend production bundle..."
cd frontend
npm ci || npm install
npm run build
cd ..

echo "[2/3] Setting up backend environment..."
cd backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt reportlab pillow

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "[3/3] Launching unified production server on http://$HOST:$PORT ..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
