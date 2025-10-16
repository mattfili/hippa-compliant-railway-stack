"""
Logging middleware for request/response tracking and structured logging.

This middleware:
- Generates unique request_id for each request
- Logs request start and completion
- Tracks request duration
- Redacts sensitive data from logs (Authorization headers, PHI)
- Adds request_id to response headers for client correlation
"""

import logging
import time
import uuid
import re
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import request_id_ctx, user_id_ctx, info_with_context

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging with HIPAA-compliant sanitization.

    Logs all requests with structured context and sanitizes sensitive data.
    """

    # Sensitive query parameters to redact (HIPAA PHI)
    SENSITIVE_PARAMS = {
        "patient_id",
        "ssn",
        "medical_record_number",
        "mrn",
        "date_of_birth",
        "dob",
        "phone",
        "email",
        "address",
    }

    # Request headers to redact
    SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "cookie",
        "x-auth-token",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging and context injection.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            Response: HTTP response with request_id header
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Set request_id in logging context
        request_id_token = request_id_ctx.set(request_id)

        # Store request_id in request state for downstream access
        request.state.request_id = request_id

        # Record start time
        start_time = time.time()

        # Sanitize query parameters for logging
        sanitized_params = self._sanitize_query_params(dict(request.query_params))

        # Log request start (DEBUG level)
        logger.debug(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "context": {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": sanitized_params,
                    "client_host": request.client.host if request.client else None,
                }
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000

            # Add request_id to response headers for client correlation
            response.headers["X-Request-ID"] = request_id

            # Extract user_id from request state if available
            user_id = None
            if hasattr(request.state, "user_context"):
                user_id = request.state.user_context.user_id
                user_id_token = user_id_ctx.set(user_id)
            else:
                user_id_token = None

            try:
                # Log request completion (INFO level)
                info_with_context(
                    logger,
                    f"Request completed: {request.method} {request.url.path}",
                    context={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                        "user_id": user_id,
                    },
                )
            finally:
                # Reset user_id context if it was set
                if user_id_token:
                    user_id_ctx.reset(user_id_token)

            return response

        except Exception as e:
            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000

            # Log request failure (ERROR level)
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "context": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration_ms, 2),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
                exc_info=True,
            )

            # Re-raise exception to be handled by exception middleware
            raise

        finally:
            # Reset request_id context
            request_id_ctx.reset(request_id_token)

    def _sanitize_query_params(self, params: dict) -> dict:
        """
        Sanitize query parameters by redacting sensitive values.

        Args:
            params: Dictionary of query parameters

        Returns:
            dict: Sanitized query parameters with sensitive values redacted
        """
        sanitized = {}
        for key, value in params.items():
            # Check if parameter name is sensitive
            if key.lower() in self.SENSITIVE_PARAMS:
                sanitized[key] = "***"
            else:
                # Check if value looks like PHI (basic heuristics)
                if self._looks_like_phi(str(value)):
                    sanitized[key] = "***"
                else:
                    sanitized[key] = value

        return sanitized

    def _looks_like_phi(self, value: str) -> bool:
        """
        Heuristic check if value looks like PHI.

        Args:
            value: Query parameter value

        Returns:
            bool: True if value looks like PHI
        """
        # Check for SSN pattern (XXX-XX-XXXX or XXXXXXXXX)
        if re.match(r"^\d{3}-?\d{2}-?\d{4}$", value):
            return True

        # Check for phone number pattern
        if re.match(r"^\+?1?\d{10,}$", value.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")):
            return True

        # Check for email pattern
        if "@" in value and "." in value:
            return True

        return False
