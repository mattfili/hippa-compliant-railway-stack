"""
FastAPI application factory and main application instance.

This module creates and configures the FastAPI application with:
- CORS middleware with environment-based origin configuration
- Exception handling middleware for standardized error responses
- Logging middleware with request tracking
- Tenant context middleware for multi-tenant isolation
- Structured JSON logging
- OpenAPI documentation
- API route registration
- Root health check endpoint
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.exception import ExceptionHandlerMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.tenant_context import TenantContextMiddleware
from app.utils.logger import setup_logging

# Import API routers
from app.api.v1 import auth, health

logger = logging.getLogger(__name__)

# Application metadata
APP_TITLE = "HIPAA-Compliant Backend API"
APP_DESCRIPTION = """
Production-ready FastAPI backend with OIDC/SAML authentication,
multi-tenant context management, and HIPAA-compliant infrastructure patterns.

## Features

- **JWT Authentication**: Token validation with JWKS endpoint integration
- **Multi-Tenant Context**: Automatic tenant isolation from JWT claims
- **HIPAA Compliance**: Structured logging, encryption, and audit trails
- **Health Checks**: Liveness and readiness endpoints for orchestration
- **Standardized Error Handling**: Error code registry with detailed logging

## API Endpoints

### Authentication (`/api/v1/auth`)
- **POST /api/v1/auth/callback**: Handle IdP callback and exchange auth code for JWT
- **GET /api/v1/auth/validate**: Validate current user's JWT token
- **POST /api/v1/auth/logout**: Logout and return IdP logout URL

### Health (`/api/v1/health`)
- **GET /api/v1/health/live**: Liveness probe (always returns 200 unless crashed)
- **GET /api/v1/health/ready**: Readiness probe (checks database connectivity)
"""
APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Configure logging, initialize services
    - Shutdown: Clean up resources

    Args:
        app: FastAPI application instance
    """
    # Startup
    settings = get_settings()

    # Configure structured logging
    enable_json = not settings.is_development()  # Use simple format in development
    setup_logging(log_level=settings.log_level, enable_json=enable_json)

    logger.info(
        f"Application starting in {settings.environment} environment",
        extra={
            "context": {
                "environment": settings.environment,
                "log_level": settings.log_level,
                "json_logging": enable_json,
            }
        },
    )

    yield

    # Shutdown
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """
    FastAPI application factory.

    Creates and configures the FastAPI application instance with:
    - Structured JSON logging
    - Exception handling middleware
    - Request logging middleware
    - Tenant context middleware
    - CORS middleware
    - API route registration
    - OpenAPI documentation

    Middleware execution order (outer to inner):
    1. ExceptionHandlerMiddleware (catches all errors)
    2. LoggingMiddleware (logs requests/responses, generates request_id)
    3. CORSMiddleware (handles CORS headers)
    4. TenantContextMiddleware (extracts tenant context)
    5. Route handlers

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Get settings
    settings = get_settings()

    # Add exception handling middleware (first in chain, catches all errors)
    app.add_middleware(ExceptionHandlerMiddleware)

    # Add logging middleware (second in chain, logs all requests)
    app.add_middleware(LoggingMiddleware)

    # CORS configuration with environment-based origins
    # Production origins should be configured via ALLOWED_ORIGINS environment variable
    # Development defaults to common localhost ports
    allowed_origins = settings.get_allowed_origins_list()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,  # Required for cookie-based refresh tokens
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=86400,  # 24 hours - preflight request caching
    )

    # Add tenant context middleware (after CORS, before routes)
    app.add_middleware(TenantContextMiddleware)

    # Register API routers
    # Health check endpoints (no authentication required)
    app.include_router(health.router)

    # Authentication endpoints
    app.include_router(auth.router)

    logger.info("API routers registered: health, auth")

    # Root endpoint for basic health check
    @app.get("/", tags=["Root"])
    async def root():
        """
        Root endpoint returning basic status.

        This is a simple health check that always returns 200 OK
        if the application is running.

        Returns:
            dict: Status indicator
        """
        return {"status": "ok"}

    return app


# Create application instance
app = create_app()
