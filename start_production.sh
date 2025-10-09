#!/bin/bash

echo "============================================"
echo "Starting NDA Redline Production System"
echo "============================================"
echo

echo "[1/4] Starting Redis container..."
docker compose up -d redis
sleep 3

echo "[2/4] Checking Redis connection..."
docker exec nda_redis redis-cli ping
if [ $? -ne 0 ]; then
    echo "ERROR: Redis is not responding"
    echo "Please ensure Docker is installed and running"
    exit 1
fi

echo "[3/4] Redis Commander available at http://localhost:8081"
docker compose up -d redis-commander
sleep 2

echo "[4/4] Starting NDA backend server..."
cd backend
python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

sleep 5
echo
echo "============================================"
echo "System Started Successfully!"
echo "============================================"
echo
echo "Services:"
echo "- Backend API: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo "- Redis Commander: http://localhost:8081"
echo "- Metrics: http://localhost:8000/metrics"
echo
echo "New Endpoints:"
echo "- Batch Upload: POST http://localhost:8000/api/batch/upload"
echo "- Batch Status: GET http://localhost:8000/api/batch/status/{batch_id}"
echo "- Statistics: GET http://localhost:8000/api/stats"
echo
echo "Press Ctrl+C to stop all services..."

# Wait for user interrupt
trap "echo 'Stopping services...'; kill $BACKEND_PID; docker compose down; exit" INT
wait