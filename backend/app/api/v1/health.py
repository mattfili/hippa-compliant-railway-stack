"""
Health check API endpoints for Kubernetes-style liveness and readiness probes.

This module provides:
- GET /api/v1/health/live - Liveness probe (always returns 200 unless crashed)
- GET /api/v1/health/ready - Readiness probe (checks database connectivity)

These endpoints do NOT require authentication and are used by orchestrators
to determine service health status.
"""

import logging
import time
from typing import Dict, Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database.engine import get_engine
from app.utils.errors import ErrorCode, format_error_response

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/api/v1/health",
    tags=["Health"],
)


# Response Models

class LivenessResponse(BaseModel):
    """Response from liveness probe endpoint."""

    status: str = Field(..., description="Service status (always 'ok' unless crashed)")
    timestamp: int = Field(..., description="Current Unix timestamp")


class ReadinessCheck(BaseModel):
    """Individual readiness check status."""

    status: str = Field(..., description="Check status: 'ok', 'degraded', or 'unavailable'")
    latency_ms: int | None = Field(None, description="Check latency in milliseconds")
    error: str | None = Field(None, description="Error message if check failed")


class ReadinessResponse(BaseModel):
    """Response from readiness probe endpoint."""

    status: str = Field(
        ...,
        description="Overall status: 'ready' (all ok), 'degraded' (some failed), or 'unavailable' (critical failed)",
    )
    checks: Dict[str, ReadinessCheck] = Field(..., description="Individual dependency check results")
    timestamp: int = Field(..., description="Current Unix timestamp")


# Endpoints

@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="""
    Kubernetes-style liveness probe endpoint.

    This endpoint always returns 200 OK if the application process is running.
    It does not check external dependencies.

    Use this endpoint to determine if the application needs to be restarted.
    If this endpoint fails to respond, the orchestrator should restart the container.

    Target response time: < 100ms
    """,
    responses={
        200: {
            "description": "Application is alive",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "timestamp": 1234567890,
                    }
                }
            },
        },
    },
)
async def liveness_probe() -> LivenessResponse:
    """
    Liveness probe endpoint.

    Returns 200 OK if the application is running. Does not check dependencies.
    This is a fast check (< 100ms) used by Kubernetes to determine if the
    application needs to be restarted.

    Returns:
        LivenessResponse: Status indicator with timestamp
    """
    current_timestamp = int(time.time())

    return LivenessResponse(
        status="ok",
        timestamp=current_timestamp,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="""
    Kubernetes-style readiness probe endpoint.

    This endpoint checks critical dependencies before returning 200 OK:
    - Database connectivity (executes simple query)

    If any critical dependency is unavailable, returns 503 Service Unavailable.

    Use this endpoint to determine if the application is ready to receive traffic.
    If this endpoint returns 503, the orchestrator should not route traffic
    to this instance.

    Target response time: < 500ms
    """,
    responses={
        200: {
            "description": "Application is ready to receive traffic",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ready",
                        "checks": {
                            "database": {
                                "status": "ok",
                                "latency_ms": 15,
                                "error": None,
                            }
                        },
                        "timestamp": 1234567890,
                    }
                }
            },
        },
        503: {
            "description": "Application is not ready (dependencies unavailable)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unavailable",
                        "checks": {
                            "database": {
                                "status": "unavailable",
                                "latency_ms": None,
                                "error": "Connection timeout",
                            }
                        },
                        "timestamp": 1234567890,
                    }
                }
            },
        },
    },
)
async def readiness_probe(response: Response) -> ReadinessResponse:
    """
    Readiness probe endpoint with dependency checks.

    Checks database connectivity and returns appropriate status.
    Returns 503 if critical dependencies are unavailable.

    Args:
        response: FastAPI response object (for setting status code)

    Returns:
        ReadinessResponse: Status indicator with dependency check results
    """
    current_timestamp = int(time.time())
    checks: Dict[str, ReadinessCheck] = {}
    all_ok = True

    # Check database connectivity
    db_check_start = time.time()
    try:
        engine = get_engine()

        # Execute simple query to verify connectivity
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        db_latency_ms = int((time.time() - db_check_start) * 1000)

        checks["database"] = ReadinessCheck(
            status="ok",
            latency_ms=db_latency_ms,
            error=None,
        )

        logger.debug(
            f"Database health check passed (latency: {db_latency_ms}ms)",
            extra={
                "context": {
                    "check": "database",
                    "latency_ms": db_latency_ms,
                }
            },
        )

    except RuntimeError as e:
        # Engine not initialized - this is expected during startup
        checks["database"] = ReadinessCheck(
            status="unavailable",
            latency_ms=None,
            error="Database engine not initialized",
        )
        all_ok = False

        logger.warning(
            "Database health check failed: engine not initialized",
            extra={
                "context": {
                    "check": "database",
                    "error": str(e),
                }
            },
        )

    except Exception as e:
        db_latency_ms = int((time.time() - db_check_start) * 1000)

        checks["database"] = ReadinessCheck(
            status="unavailable",
            latency_ms=db_latency_ms if db_latency_ms < 5000 else None,
            error=str(e),
        )
        all_ok = False

        logger.warning(
            f"Database health check failed: {str(e)}",
            extra={
                "context": {
                    "check": "database",
                    "error": str(e),
                    "latency_ms": db_latency_ms,
                }
            },
        )

    # Determine overall status
    if all_ok:
        overall_status = "ready"
        response.status_code = status.HTTP_200_OK
    else:
        overall_status = "unavailable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=overall_status,
        checks=checks,
        timestamp=current_timestamp,
    )
