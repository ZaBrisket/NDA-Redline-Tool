#!/bin/bash

echo "============================================"
echo "Starting NDA Redline Tool on Railway"
echo "============================================"
echo

# Install backend dependencies if needed
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt

# Set default environment variables for Railway if not present
export PORT=${PORT:-8000}
export PYTHONUNBUFFERED=1

# Create necessary directories
mkdir -p storage/uploads
mkdir -p storage/processed
mkdir -p storage/cache
mkdir -p storage/logs
mkdir -p storage/audit

echo "Starting backend server on port $PORT..."
# Use uvicorn directly for Railway deployment
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT

echo "Server started successfully!"