#!/usr/bin/env bash
# EnergyGuardian AI — start the backend API and the frontend dev server together.
# Usage:  ./run.sh        (from the v2 folder)
# Stop:   Ctrl+C          (stops both)

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/../.venv"

# 1. Python venv (create + install if missing)
if [ ! -d "$VENV" ]; then
  echo "→ Creating Python venv and installing backend deps…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r "$HERE/requirements.txt"
fi

# 2. Frontend deps (install if missing)
if [ ! -d "$HERE/frontend/node_modules" ]; then
  echo "→ Installing frontend deps…"
  (cd "$HERE/frontend" && npm install)
fi

# 3. Free the ports if something is already listening
lsof -ti:5001 | xargs kill -9 2>/dev/null || true

# 4. Start the backend API (port 5001)
echo "→ Starting API on http://localhost:5001"
"$VENV/bin/python" "$HERE/api.py" &
API_PID=$!

# 5. Start the frontend dev server
echo "→ Starting frontend on http://localhost:5173"
(cd "$HERE/frontend" && npm run dev) &
WEB_PID=$!

# 6. Stop both cleanly on Ctrl+C
trap 'echo; echo "→ Stopping…"; kill $API_PID $WEB_PID 2>/dev/null; exit 0' INT TERM

echo
echo "======================================================================"
echo "  EnergyGuardian AI is starting."
echo "  Open the dashboard:   http://localhost:5173"
echo "  (API/data endpoint:   http://localhost:5001  — no homepage, that's normal)"
echo "  Press Ctrl+C to stop both servers."
echo "======================================================================"
wait
