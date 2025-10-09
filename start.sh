#!/bin/bash

echo "============================================"
echo "Starting NDA Redline Tool on Railway"
echo "============================================"
echo "Railway Project: ${RAILWAY_PROJECT_NAME}"
echo "Environment: ${RAILWAY_ENVIRONMENT_NAME}"
echo "Service: ${RAILWAY_SERVICE_NAME}"
echo "============================================"
echo

# Install backend dependencies if needed
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt

# Validate environment before starting
echo
echo "Validating environment configuration..."
cd ..
python validate_env.py
if [ $? -ne 0 ]; then
    echo "Environment validation failed. Please check your configuration."
    exit 1
fi
cd backend

# Set default environment variables for Railway if not present
export PORT=${PORT:-8000}
export PYTHONUNBUFFERED=1

# Disable Redis features if REDIS_URL is not set
if [ -z "$REDIS_URL" ]; then
    echo "No Redis URL found - disabling Redis features"
    export USE_REDIS_QUEUE=false
    export ENABLE_SEMANTIC_CACHE=false
else
    echo "Redis URL found - Redis features enabled"
fi

# Create necessary directories
echo "Creating storage directories..."
mkdir -p storage/uploads
mkdir -p storage/processed
mkdir -p storage/cache
mkdir -p storage/logs
mkdir -p storage/audit

# Log environment status
echo
echo "Configuration Status:"
echo "- OpenAI API Key: $(if [ -n "$OPENAI_API_KEY" ]; then echo "✓ Configured"; else echo "✗ Missing"; fi)"
echo "- Anthropic API Key: $(if [ -n "$ANTHROPIC_API_KEY" ]; then echo "✓ Configured"; else echo "✗ Missing"; fi)"
echo "- Redis: $(if [ -n "$REDIS_URL" ]; then echo "✓ Connected"; else echo "○ Not configured (caching disabled)"; fi)"
echo "- Semantic Cache: ${ENABLE_SEMANTIC_CACHE:-false}"
echo "- Prompt Caching: ${USE_PROMPT_CACHING:-true}"
echo "- Port: $PORT"
echo

echo "Starting backend server on port $PORT..."
# Use uvicorn directly for Railway deployment
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info

echo "Server started successfully!"