#!/bin/sh
# ==============================================================================
# Startup Script for HIPAA-Compliant Backend API
# ==============================================================================
# This script runs during container startup and performs:
# 1. Database migrations using Alembic
# 2. Application server startup using Uvicorn
#
# Error handling: Exit immediately if any command fails (set -e)
# ==============================================================================

set -e

echo "=========================================="
echo "HIPAA-Compliant Backend API - Starting"
echo "=========================================="

# ------------------------------------------------------------------------------
# Database Migrations
# ------------------------------------------------------------------------------
echo ""
echo "[1/2] Running database migrations..."
echo "Executing: alembic upgrade head"

alembic upgrade head

echo "✓ Database migrations completed successfully"

# ------------------------------------------------------------------------------
# Application Startup
# ------------------------------------------------------------------------------
echo ""
echo "[2/2] Starting application server..."
echo "Executing: uvicorn app.main:app --host 0.0.0.0 --port 8000"

# Start Uvicorn with production settings
# --host 0.0.0.0: Listen on all network interfaces (required for Docker)
# --port 8000: Listen on port 8000
# --workers 1: Single worker (Railway will handle horizontal scaling)
# --proxy-headers: Trust X-Forwarded-* headers from Railway's reverse proxy
# --forwarded-allow-ips '*': Accept forwarded headers from any proxy (Railway uses dynamic IPs)

uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips '*'

# Note: We use a single worker because:
# 1. Railway handles horizontal scaling at the service level
# 2. Multiple workers can cause issues with Railway's health checks
# 3. Simpler logs and debugging with single process
# 4. Connection pooling is more efficient with single process

echo ""
echo "=========================================="
echo "Application started successfully"
echo "=========================================="
