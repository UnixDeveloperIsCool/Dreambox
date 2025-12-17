#!/bin/bash
set -e

cd "$(dirname "$0")"
source venv/bin/activate

# ---------------------------
# Load .env (server-side secrets)
# ---------------------------
set -a
[ -f .env ] && source .env
set +a

# ---------------------------
# Domain config (defaults; can be overridden in .env)
# ---------------------------
export API_BASE_URL="${API_BASE_URL:-https://api.dreamboxed.com}"
export FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-https://dreamboxinteractive.com}"
export EMAIL_FROM="${EMAIL_FROM:-no-reply@dreamboxinteractive.com}"

# ---------------------------
# SMTP defaults (override in .env)
# ---------------------------
export SMTP_HOST="${SMTP_HOST:-smtp.ionos.co.uk}"
export SMTP_PORT="${SMTP_PORT:-587}"
# SMTP_USER / SMTP_PASSWORD should be in .env for security

# ---------------------------
# Security
# ---------------------------
export SECRET_KEY="${SECRET_KEY:-9FqX6YJkT2eR8mCwL5A0nH7ZsP1dBvK4EoGxUQyJmIhVtWr}"

# Prevent python from using/creating bytecode cache (stops stale code issues)
export PYTHONDONTWRITEBYTECODE=1

# ---------------------------
# PID files (prevents duplicates without pkill)
# ---------------------------
API_PID_FILE=".api.pid"
CCU_PID_FILE=".ccu.pid"

stop_if_running () {
  local pidfile="$1"
  if [ -f "$pidfile" ]; then
    local pid
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "[run_all] Stopping old process PID=$pid from $pidfile"
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        echo "[run_all] Force killing PID=$pid"
        kill -9 "$pid" 2>/dev/null || true
      fi
    fi
    rm -f "$pidfile"
  fi
}

stop_if_running "$API_PID_FILE"
stop_if_running "$CCU_PID_FILE"

# Also clean any stray pycache (FTP deploys can leave it)
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# ---------------------------
# Start API
# ---------------------------
echo "[run_all] Starting API..."
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
echo $! > "$API_PID_FILE"

# Wait a bit for API to be up
sleep 2


# Fail fast if API died
if ! kill -0 "$(cat "$API_PID_FILE")" 2>/dev/null; then
  echo "[run_all] API crashed. Showing last 80 lines of api.log:"
  tail -n 80 api.log
  exit 1
fi



# ---------------------------
# Start CCU collector
# ---------------------------
echo "[run_all] Starting CCU collector..."
nohup python ccu_collector.py > ccu.log 2>&1 &
echo $! > "$CCU_PID_FILE"

echo "[run_all] Running."
echo "  API logs:  api.log"
echo "  CCU logs:  ccu.log"

# Keep script running in foreground if your host expects it
wait
