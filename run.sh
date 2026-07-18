#!/usr/bin/env bash
# Start backend (FastAPI) + frontend (Vite) together.
# Usage: ./run.sh
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# --- backend ---
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi
./.venv/bin/uvicorn app.main:app --port 8787 --reload &
BACK=$!

# --- frontend ---
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev &
FRONT=$!

echo ""
echo "Backend  → http://localhost:8787  (mode: $([ -n "$OPENAI_API_KEY" ] && echo llm || echo mock))"
echo "Frontend → http://localhost:5173"
echo "Ctrl-C to stop both."

trap "kill $BACK $FRONT 2>/dev/null" EXIT
wait
