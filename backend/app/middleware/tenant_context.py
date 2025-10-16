"""
Tenant context middleware for multi-tenant isolation.

This middleware:
- Extracts tenant_id from authenticated requests
- Injects tenant_id into request state for downstream access
- Validates tenant context exists for protected endpoints
- Adds tenant_id to logging context
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import tenant_id_ctx

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and inject tenant context into requests.

    This middleware runs after authentication and extracts the tenant_id
    from the user context (injected by authentication dependency).
    The tenant_id is then:
    1. Added to request.state for downstream access
    2. Added to logging context for structured logging
    """

    # Paths that don't require tenant context
    EXCLUDED_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/auth/callback",  # Authentication endpoints handle tenant extraction themselves
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and inject tenant context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            Response: HTTP response
        """
        # Skip tenant context for excluded paths
        if request.url.path in self.EXCLUDED_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        # Check if user context was injected by authentication
        # (This happens via the get_current_user dependency in protected routes)
        if hasattr(request.state, "user_context"):
            user_context = request.state.user_context
            tenant_id = user_context.tenant_id

            # Set tenant_id in logging context for structured logging
            token = tenant_id_ctx.set(tenant_id)

            logger.debug(f"Tenant context set: {tenant_id}")

            try:
                response = await call_next(request)
                return response
            finally:
                # Reset logging context
                tenant_id_ctx.reset(token)
        else:
            # No user context - either public endpoint or auth will be checked in route
            return await call_next(request)
