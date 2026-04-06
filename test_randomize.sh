#!/usr/bin/env bash
# test_randomize.sh — Same as test.sh but runs spec files in random order (headless).

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
E2E_DIR="$PROJECT_ROOT/e2e"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  cd "$BACKEND_DIR" && python3 test_setup.py destroy
  echo "Done."
}
trap cleanup EXIT

echo "Stopping existing servers..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "vite"             2>/dev/null || true
sleep 1

if [ -f "$BACKEND_DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$BACKEND_DIR/.env"
  set +a
fi

echo "Destroying old test data..."
cd "$BACKEND_DIR" && python3 test_setup.py destroy

echo "Starting backend..."
cd "$BACKEND_DIR"
uvicorn main:app --port 8000 > /tmp/chess_backend.log 2>&1 &
BACKEND_PID=$!

echo "Starting frontend..."
cd "$FRONTEND_DIR"
npm run dev > /tmp/chess_frontend.log 2>&1 &
FRONTEND_PID=$!

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

echo "Seeding test data..."
cd "$BACKEND_DIR" && python3 test_setup.py create

# Build a randomly ordered list of spec files
SPECS=$(ls "$E2E_DIR/tests/"*.spec.ts | shuf | tr '\n' ' ')

echo ""
echo "Running specs in random order:"
for s in $SPECS; do
  echo "  $(basename "$s")"
done
echo ""

cd "$E2E_DIR"
npx playwright test $SPECS

# trap EXIT handles cleanup automatically
