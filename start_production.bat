@echo off
echo ============================================
echo Starting NDA Redline Production System
echo ============================================
echo.

echo [1/4] Starting Redis container...
docker compose up -d redis
timeout /t 3 >nul

echo [2/4] Checking Redis connection...
docker exec nda_redis redis-cli ping
if %errorlevel% neq 0 (
    echo ERROR: Redis is not responding
    echo Please ensure Docker is installed and running
    pause
    exit /b 1
)

echo [3/4] Redis Commander available at http://localhost:8081
docker compose up -d redis-commander
timeout /t 2 >nul

echo [4/4] Starting NDA backend server...
cd backend
start cmd /k "echo Starting NDA Backend Server && python -m uvicorn app.main:app --reload --port 8000"

timeout /t 5 >nul
echo.
echo ============================================
echo System Started Successfully!
echo ============================================
echo.
echo Services:
echo - Backend API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo - Redis Commander: http://localhost:8081
echo - Metrics: http://localhost:8000/metrics
echo.
echo New Endpoints:
echo - Batch Upload: POST http://localhost:8000/api/batch/upload
echo - Batch Status: GET http://localhost:8000/api/batch/status/{batch_id}
echo - Statistics: GET http://localhost:8000/api/stats
echo.
echo Press any key to stop monitoring (services will continue running)...
pause >nul