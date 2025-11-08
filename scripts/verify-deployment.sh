#!/bin/bash

# Deployment Verification Script
# This script verifies that all security fixes have been properly implemented

set -e

echo "=========================================="
echo "NDA Reviewer Deployment Verification"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        exit 1
    fi
}

# Check if Docker is installed
echo "1. Checking Docker installation..."
if command -v docker &> /dev/null; then
    print_status 0 "Docker is installed: $(docker --version)"
else
    print_status 1 "Docker is not installed"
fi

echo ""
echo "2. Building Docker image..."
echo "=========================================="

# Build the Docker image
docker build -t nda-reviewer:test . || print_status 1 "Docker build failed"
print_status 0 "Docker image built successfully"

echo ""
echo "3. Security Checks"
echo "=========================================="

# Check if image runs as non-root
echo "Checking non-root user..."
USER=$(docker run --rm nda-reviewer:test whoami 2>/dev/null)
if [ "$USER" == "appuser" ]; then
    print_status 0 "Container runs as non-root user: $USER"
else
    print_status 1 "Container runs as root (security issue!)"
fi

# Check image size
echo "Checking image size..."
SIZE=$(docker images nda-reviewer:test --format "{{.Size}}")
echo -e "${YELLOW}ℹ${NC} Image size: $SIZE"
# Convert size to MB for comparison
SIZE_MB=$(docker images nda-reviewer:test --format "{{.Size}}" | sed 's/MB//')
if [[ "$SIZE" == *"GB"* ]]; then
    print_status 1 "Image too large (>1GB) - likely contains build tools"
else
    print_status 0 "Image size is reasonable: $SIZE"
fi

# Check for build tools in final image
echo "Checking for build tools in final image..."
if docker run --rm nda-reviewer:test which gcc &>/dev/null; then
    print_status 1 "GCC found in image (should be removed)"
else
    print_status 0 "No GCC in final image"
fi

if docker run --rm nda-reviewer:test which make &>/dev/null; then
    print_status 1 "Make found in image (should be removed)"
else
    print_status 0 "No Make in final image"
fi

# Check for API keys in image layers
echo "Checking for secrets in image layers..."
HISTORY=$(docker history nda-reviewer:test --no-trunc 2>/dev/null)
if echo "$HISTORY" | grep -i "api_key\|anthropic_api_key" | grep -v "^#" &>/dev/null; then
    print_status 1 "Potential secrets found in image history!"
else
    print_status 0 "No secrets detected in image layers"
fi

echo ""
echo "4. File Permissions Check"
echo "=========================================="

# Check file ownership
echo "Checking file ownership..."
OWNERSHIP=$(docker run --rm nda-reviewer:test ls -ld /app | awk '{print $3":"$4}')
if [ "$OWNERSHIP" == "appuser:appuser" ]; then
    print_status 0 "App directory owned by appuser"
else
    print_status 1 "Incorrect file ownership: $OWNERSHIP"
fi

echo ""
echo "5. Runtime Test"
echo "=========================================="

# Test if the container can start
echo "Starting container for runtime test..."
CONTAINER_ID=$(docker run -d -p 8080:8080 -e PORT=8080 nda-reviewer:test 2>/dev/null)

if [ -z "$CONTAINER_ID" ]; then
    print_status 1 "Failed to start container"
else
    print_status 0 "Container started: ${CONTAINER_ID:0:12}"

    # Give it a moment to start
    sleep 5

    # Check if container is still running
    if docker ps | grep -q "$CONTAINER_ID"; then
        print_status 0 "Container is running"

        # Check health endpoint (if available)
        if curl -f http://localhost:8080/health &>/dev/null; then
            print_status 0 "Health check passed"
        else
            echo -e "${YELLOW}ℹ${NC} Health check failed (may need ANTHROPIC_API_KEY)"
        fi
    else
        print_status 1 "Container stopped unexpectedly"
        echo "Container logs:"
        docker logs "$CONTAINER_ID"
    fi

    # Cleanup
    docker stop "$CONTAINER_ID" &>/dev/null
    docker rm "$CONTAINER_ID" &>/dev/null
fi

echo ""
echo "6. Configuration Files Check"
echo "=========================================="

# Check if .dockerignore exists
if [ -f ".dockerignore" ]; then
    print_status 0 ".dockerignore file exists"

    # Check for critical patterns
    if grep -q "\.env" .dockerignore; then
        print_status 0 ".env files excluded in .dockerignore"
    else
        print_status 1 ".env not excluded in .dockerignore"
    fi
else
    print_status 1 ".dockerignore file missing"
fi

# Check if Dockerfile exists
if [ -f "Dockerfile" ]; then
    print_status 0 "Dockerfile exists"

    # Check for multi-stage build
    if grep -q "FROM.*AS builder" Dockerfile && grep -q "FROM.*AS runtime" Dockerfile; then
        print_status 0 "Multi-stage build configured"
    else
        print_status 1 "Multi-stage build not configured"
    fi

    # Check for USER directive
    if grep -q "^USER appuser" Dockerfile; then
        print_status 0 "USER directive found in Dockerfile"
    else
        print_status 1 "No USER directive in Dockerfile"
    fi
else
    print_status 1 "Dockerfile missing"
fi

# Check railway.json configuration
if [ -f "railway.json" ]; then
    print_status 0 "railway.json exists"

    # Check for Docker builder
    if grep -q '"builder": "DOCKERFILE"' railway.json; then
        print_status 0 "Railway configured to use Docker"
    else
        print_status 1 "Railway not using Docker builder"
    fi
else
    print_status 1 "railway.json missing"
fi

# Check that nixpacks.toml is removed
if [ -f "nixpacks.toml" ]; then
    print_status 1 "nixpacks.toml still exists (should be removed)"
else
    print_status 0 "nixpacks.toml removed"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Verification Complete!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "- Docker image builds successfully"
echo "- Runs as non-root user (appuser)"
echo "- No build tools in final image"
echo "- No secrets in image layers"
echo "- Proper file permissions"
echo "- All configuration files in place"
echo ""
echo -e "${YELLOW}Note:${NC} Some runtime features may require environment variables"
echo "      (e.g., ANTHROPIC_API_KEY) to be set in Railway dashboard."
echo ""