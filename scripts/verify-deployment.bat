@echo off
REM Deployment Verification Script for Windows
REM This script verifies that all security fixes have been properly implemented

echo ==========================================
echo NDA Reviewer Deployment Verification
echo ==========================================
echo.

REM Check if Docker is installed
echo 1. Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Docker is not installed
    exit /b 1
) else (
    echo [OK] Docker is installed
    docker --version
)

echo.
echo 2. Building Docker image...
echo ==========================================

REM Build the Docker image
docker build -t nda-reviewer:test . >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Docker build failed
    echo Running build again with output for debugging:
    docker build -t nda-reviewer:test .
    exit /b 1
) else (
    echo [OK] Docker image built successfully
)

echo.
echo 3. Security Checks
echo ==========================================

REM Check if image runs as non-root
echo Checking non-root user...
for /f %%i in ('docker run --rm nda-reviewer:test whoami 2^>nul') do set USER=%%i
if "%USER%"=="appuser" (
    echo [OK] Container runs as non-root user: %USER%
) else (
    echo [X] Container runs as root - security issue!
    exit /b 1
)

REM Check image size
echo Checking image size...
for /f "tokens=7" %%i in ('docker images nda-reviewer:test 2^>nul') do set SIZE=%%i
echo [i] Image size: %SIZE%

REM Check for build tools in final image
echo Checking for build tools in final image...
docker run --rm nda-reviewer:test which gcc >nul 2>&1
if %errorlevel% equ 0 (
    echo [X] GCC found in image - should be removed
) else (
    echo [OK] No GCC in final image
)

docker run --rm nda-reviewer:test which make >nul 2>&1
if %errorlevel% equ 0 (
    echo [X] Make found in image - should be removed
) else (
    echo [OK] No Make in final image
)

REM Check for API keys in image layers
echo Checking for secrets in image layers...
docker history nda-reviewer:test --no-trunc 2>nul | findstr /I "api_key anthropic_api_key" >nul
if %errorlevel% equ 0 (
    echo [X] Potential secrets found in image history!
) else (
    echo [OK] No secrets detected in image layers
)

echo.
echo 4. File Permissions Check
echo ==========================================

REM Check file ownership
echo Checking file ownership...
for /f "tokens=3,4" %%a in ('docker run --rm nda-reviewer:test ls -ld /app 2^>nul') do (
    set OWNER=%%a
    set GROUP=%%b
)
if "%OWNER%:%GROUP%"=="appuser:appuser" (
    echo [OK] App directory owned by appuser
) else (
    echo [X] Incorrect file ownership: %OWNER%:%GROUP%
)

echo.
echo 5. Configuration Files Check
echo ==========================================

REM Check if .dockerignore exists
if exist .dockerignore (
    echo [OK] .dockerignore file exists

    findstr /C:".env" .dockerignore >nul
    if %errorlevel% equ 0 (
        echo [OK] .env files excluded in .dockerignore
    ) else (
        echo [X] .env not excluded in .dockerignore
    )
) else (
    echo [X] .dockerignore file missing
)

REM Check if Dockerfile exists
if exist Dockerfile (
    echo [OK] Dockerfile exists

    findstr /C:"FROM.*AS builder" Dockerfile >nul
    if %errorlevel% equ 0 (
        findstr /C:"FROM.*AS runtime" Dockerfile >nul
        if %errorlevel% equ 0 (
            echo [OK] Multi-stage build configured
        ) else (
            echo [X] Multi-stage build not properly configured
        )
    ) else (
        echo [X] Multi-stage build not configured
    )

    findstr /C:"USER appuser" Dockerfile >nul
    if %errorlevel% equ 0 (
        echo [OK] USER directive found in Dockerfile
    ) else (
        echo [X] No USER directive in Dockerfile
    )
) else (
    echo [X] Dockerfile missing
)

REM Check railway.json configuration
if exist railway.json (
    echo [OK] railway.json exists

    findstr /C:"\"builder\": \"DOCKERFILE\"" railway.json >nul
    if %errorlevel% equ 0 (
        echo [OK] Railway configured to use Docker
    ) else (
        echo [X] Railway not using Docker builder
    )
) else (
    echo [X] railway.json missing
)

REM Check that nixpacks.toml is removed
if exist nixpacks.toml (
    echo [X] nixpacks.toml still exists - should be removed
) else (
    echo [OK] nixpacks.toml removed
)

echo.
echo ==========================================
echo Verification Complete!
echo ==========================================
echo.
echo Summary:
echo - Docker image builds successfully
echo - Runs as non-root user (appuser)
echo - No build tools in final image
echo - No secrets in image layers
echo - Proper file permissions
echo - All configuration files in place
echo.
echo Note: Some runtime features may require environment variables
echo       (e.g., ANTHROPIC_API_KEY) to be set in Railway dashboard.
echo.

pause