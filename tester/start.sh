#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "→ Creating virtual environment…"
  python3 -m venv .venv
fi

# Install dependencies
echo "→ Installing dependencies…"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

# Copy .env if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "→ Created .env from .env.example – edit it if needed"
fi

PORT=${PORT:-8090}
echo "→ Starting Honeypot Tester on http://localhost:${PORT}"
.venv/bin/uvicorn app:app --host 0.0.0.0 --port "$PORT" --reload
