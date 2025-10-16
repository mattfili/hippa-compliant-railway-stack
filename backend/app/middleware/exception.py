"""
Exception handling middleware for standardized error responses.

This middleware:
- Catches all unhandled exceptions
- Converts exceptions to standardized error format
- Logs exceptions with full stack trace (ERROR level)
- Returns appropriate HTTP status codes
- Never exposes stack traces to clients (only in logs)
"""

import logging
import traceback
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.errors import (
    APIException,
    ErrorCode,
    format_error_response,
)

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches all exceptions and converts them to standardized error responses.

    This middleware ensures that:
    1. All APIException instances return their defined error format
    2. Unhandled exceptions are logged with full stack trace
    3. Clients receive safe, standardized error responses
    4. Stack traces are never exposed to clients (HIPAA compliance)
    5. Request ID is included in error responses for log correlation
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle any exceptions.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler in the chain

        Returns:
            Response: HTTP response (either successful or error response)
        """
        try:
            # Attempt to process the request
            response = await call_next(request)
            return response

        except APIException as exc:
            # Handle our custom API exceptions with defined error codes
            return await self._handle_api_exception(request, exc)

        except Exception as exc:
            # Handle all other unexpected exceptions
            return await self._handle_unexpected_exception(request, exc)

    async def _handle_api_exception(
        self, request: Request, exc: APIException
    ) -> JSONResponse:
        """
        Handle custom API exceptions.

        Args:
            request: HTTP request
            exc: API exception instance

        Returns:
            JSONResponse with standardized error format
        """
        # Get request ID from request state if available
        request_id = getattr(request.state, "request_id", None)

        # Determine if we should include detail (only in development)
        # In production, we don't expose technical details to clients
        include_detail = self._should_include_detail(request)

        # Log the error with context
        logger.error(
            f"API Exception: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "detail": exc.detail,
            },
        )

        # Format error response
        error_response = format_error_response(
            error_code=exc.error_code,
            message=exc.message,
            detail=exc.detail,
            request_id=request_id,
            include_detail=include_detail,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
        )

    async def _handle_unexpected_exception(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Handle unexpected exceptions.

        Logs full stack trace but returns generic error to client.

        Args:
            request: HTTP request
            exc: Unexpected exception

        Returns:
            JSONResponse with generic internal server error
        """
        # Get request ID from request state if available
        request_id = getattr(request.state, "request_id", None)

        # Get full stack trace for logging
        stack_trace = traceback.format_exc()

        # Log the full exception with stack trace
        logger.error(
            f"Unexpected exception: {type(exc).__name__}: {str(exc)}",
            extra={
                "error_code": ErrorCode.SYS_INTERNAL_ERROR,
                "status_code": 500,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "stack_trace": stack_trace,
            },
        )

        # Determine if we should include detail (only in development)
        include_detail = self._should_include_detail(request)

        # Return generic internal server error
        # NEVER expose stack traces or internal details to clients
        error_response = format_error_response(
            error_code=ErrorCode.SYS_INTERNAL_ERROR,
            message="An unexpected error occurred",
            detail=str(exc) if include_detail else None,
            request_id=request_id,
            include_detail=include_detail,
        )

        return JSONResponse(
            status_code=500,
            content=error_response,
        )

    def _should_include_detail(self, request: Request) -> bool:
        """
        Determine if technical details should be included in error response.

        Details are only included in development environment.
        In production, we never expose technical details for security/HIPAA compliance.

        Args:
            request: HTTP request

        Returns:
            bool: True if details should be included
        """
        # Check if ENVIRONMENT is set to development
        # This should be configured via environment variable
        import os
        environment = os.getenv("ENVIRONMENT", "production").lower()
        return environment == "development"
