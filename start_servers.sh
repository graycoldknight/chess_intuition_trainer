#!/bin/bash

# Get local IP (first non-loopback IP)
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Local IP: $LOCAL_IP"
echo "Frontend will be accessible at: http://$LOCAL_IP:5174"
echo "Backend will be accessible at: http://$LOCAL_IP:8000"
echo ""

# Update CORS in main.py if IP not already present
if ! grep -q "http://$LOCAL_IP:5174" backend/main.py; then
    echo "Adding $LOCAL_IP:5174 to CORS..."
    # Escape slashes for sed
    ESCAPED_IP=$(echo "http://$LOCAL_IP:5174" | sed 's/\//\\\//g')
    sed -i "s/allow_origins=\[/allow_origins=[\"$ESCAPED_IP\", /" backend/main.py
    echo "CORS updated in main.py"
else
    echo "CORS already configured for $LOCAL_IP:5174"
fi
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
