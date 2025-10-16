# ==============================================================================
# Multi-Stage Dockerfile for HIPAA-Compliant Backend API
# ==============================================================================
# This Dockerfile uses a multi-stage build to:
# 1. Build dependencies in an isolated builder stage
# 2. Create a minimal production image with only runtime dependencies
# 3. Optimize image size and security surface area
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------------------------
# Install dependencies using uv package manager
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --frozen ensures exact versions from lockfile are used
RUN uv sync --frozen

# ------------------------------------------------------------------------------
# Stage 2: Runtime
# ------------------------------------------------------------------------------
# Create minimal production image
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder stage
# This includes all installed dependencies
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ app/

# Copy Alembic migration files
COPY alembic/ alembic/
COPY alembic.ini .

# Copy startup script
COPY scripts/ scripts/

# Set PATH to include virtual environment binaries
ENV PATH="/app/.venv/bin:$PATH"

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Health check for container orchestration
# Checks the liveness endpoint every 30 seconds
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/live')" || exit 1

# Run startup script that executes migrations and starts the application
CMD ["sh", "scripts/startup.sh"]
