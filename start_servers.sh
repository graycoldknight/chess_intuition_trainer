#!/bin/bash

# Get local IP (first non-loopback IP)
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Local IP: $LOCAL_IP"
echo "Frontend will be accessible at: http://$LOCAL_IP:5174"
echo "Backend will be accessible at: http://$LOCAL_IP:8000"
echo ""


# Kill any existing servers
echo "Killing any existing servers on 5173/5174/8000..."
lsof -ti:5173,5174,8000 | xargs kill -9 2>/dev/null || true
sleep 1

echo "Starting servers..."
echo ""

# Start backend
cd backend
echo "Starting backend on port 8000..."
uvicorn main:app --port 8000 --host 0.0.0.0 --reload &
BACKEND_PID=$!
sleep 2

# Start frontend
cd ../frontend
echo "Starting frontend on port 5174..."
npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "Both servers started!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for both
wait
