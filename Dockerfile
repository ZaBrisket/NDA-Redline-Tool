# Multi-stage Docker build for NDA Reviewer API
# Stage 1: Builder - Contains build dependencies
# Stage 2: Runtime - Minimal production image

# ============================================
# STAGE 1: BUILDER
# ============================================
FROM python:3.11-bullseye AS builder

# Install system dependencies required for building Python packages
# These will NOT be in the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Create virtual environment in a known location
RUN python -m venv /opt/venv

# Ensure we use the virtualenv for all operations
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip to latest version for better dependency resolution
RUN pip install --upgrade pip setuptools wheel

# Copy only requirements first (for better caching)
# This allows Docker to cache the dependency layer if requirements haven't changed
COPY backend/requirements.txt /build/requirements.txt

# Install Python dependencies
# Using --no-cache-dir to keep the builder stage cleaner
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# STAGE 2: RUNTIME (PRODUCTION)
# ============================================
FROM python:3.11-slim-bullseye AS runtime

# Install only essential runtime dependencies
# No compilers or build tools in the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl1.1 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for running the application
# Using a high UID to avoid conflicts with host UIDs
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -d /app -s /bin/bash appuser

# Set up application directory
WORKDIR /app

# Copy virtual environment from builder stage
# This contains all our Python dependencies without build tools
COPY --from=builder /opt/venv /opt/venv

# Copy backend application code
# Ensure proper ownership for the non-root user
COPY --chown=appuser:appuser backend/ /app/backend/

# Copy configuration files to root directory
# These are needed for the application to find its config
COPY --chown=appuser:appuser Procfile /app/
COPY --chown=appuser:appuser railway.json /app/

# Ensure virtual environment is in PATH
ENV PATH="/opt/venv/bin:$PATH"

# Python optimizations for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=UTF-8 \
    # Prevents Python from loading modules from user site directory
    PYTHONNOUSERSITE=1 \
    # Ensures consistent behavior
    PYTHONHASHSEED=random

# Application-specific environment variables
# These are runtime configuration, NOT secrets
ENV LOG_FORMAT=json \
    LOG_LEVEL=info \
    # Tell the app it's running in a containerized environment
    CONTAINER_ENV=railway

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Health check endpoint
# Railway will use this to determine if the container is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Switch to non-root user
# All subsequent operations will run as this user
USER appuser

# Expose port (Railway will override with PORT env var)
# This is mainly for documentation purposes
EXPOSE 8080

# Set the working directory for the runtime
WORKDIR /app/backend

# Default command (can be overridden by railway.json or Procfile)
# Using exec form to ensure proper signal handling
CMD ["/opt/venv/bin/gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]

# ============================================
# SECURITY & BEST PRACTICES IMPLEMENTED:
# ============================================
# 1. Multi-stage build to minimize final image size
# 2. Non-root user (appuser) for running the application
# 3. No build tools (gcc, g++) in final image
# 4. Minimal base image (python-slim)
# 5. Proper layer caching with requirements.txt copied first
# 6. No secrets or API keys in the image
# 7. Health check configured
# 8. Proper signal handling with exec form CMD
# 9. Read-only Python bytecode settings
# 10. Explicit PATH configuration for virtual environment