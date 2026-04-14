#!/usr/bin/env bash
# test.sh — Kill servers, reset test data, restart, then open Playwright UI

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
E2E_DIR="$PROJECT_ROOT/e2e"

BACKEND_PID=""
FRONTEND_PID=""

# ── Cleanup on exit ────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  cd "$BACKEND_DIR" && python3 test_setup.py destroy
  echo "Done."
}
trap cleanup EXIT

# ── Kill any already-running instances ────────────────────────────
echo "Stopping existing servers..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "vite"             2>/dev/null || true
sleep 1

# ── Load env vars (Gemini API key needed by test_setup.py) ────────
if [ -f "$BACKEND_DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$BACKEND_DIR/.env"
  set +a
fi

# ── Clean up stale test data ───────────────────────────────────────
echo "Destroying old test data..."
cd "$BACKEND_DIR" && python3 test_setup.py destroy

# ── Start backend ─────────────────────────────────────────────────
echo "Starting backend..."
cd "$BACKEND_DIR"
uvicorn main:app --port 8000 > /tmp/chess_backend.log 2>&1 &
BACKEND_PID=$!

# ── Start frontend ────────────────────────────────────────────────
echo "Starting frontend..."
cd "$FRONTEND_DIR"
npm run dev > /tmp/chess_frontend.log 2>&1 &
FRONTEND_PID=$!

# ── Wait for backend ──────────────────────────────────────────────
echo -n "Waiting for backend..."
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo " ready"
    break
  fi
  echo -n "."
  sleep 1
  if [ "$i" -eq 30 ]; then
    echo " TIMEOUT — check /tmp/chess_backend.log"
    exit 1
  fi
done

# ── Wait for frontend ─────────────────────────────────────────────
echo -n "Waiting for frontend..."
for i in $(seq 1 30); do
  if curl -s http://localhost:5173/ > /dev/null 2>&1; then
    echo " ready"
    break
  fi
  echo -n "."
  sleep 1
  if [ "$i" -eq 30 ]; then
    echo " TIMEOUT — check /tmp/chess_frontend.log"
    exit 1
  fi
done

# ── Seed fresh test data ──────────────────────────────────────────
echo "Seeding test data..."
cd "$BACKEND_DIR" && python3 test_setup.py create

# ── Launch Playwright UI ──────────────────────────────────────────
echo ""
echo "Opening Playwright UI — close the window when done."
cd "$E2E_DIR"
npx playwright test --ui

# trap EXIT handles cleanup automatically when playwright UI is closed
