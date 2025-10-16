"""
Error registry and custom exception classes for standardized error handling.

This module provides:
- Error code registry with AUTH, SYS, and VAL error codes
- Custom exception classes for different error types
- Standardized error response formatter
- Error code to HTTP status code mapping
"""

from typing import Any, Dict, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """
    Centralized error code registry.

    Error codes are organized by domain:
    - AUTH_xxx: Authentication and authorization errors (001-999)
    - SYS_xxx: System and infrastructure errors (001-999)
    - VAL_xxx: Validation errors (001-999)
    """

    # Authentication Errors (AUTH_001 - AUTH_999)
    AUTH_INVALID_TOKEN = "AUTH_001"  # Invalid token (signature verification failed)
    AUTH_CSRF_FAILED = "AUTH_002"  # CSRF validation failed
    AUTH_TOKEN_EXPIRED = "AUTH_003"  # Token expired
    AUTH_INVALID_SIGNATURE = "AUTH_004"  # Invalid token signature
    AUTH_MISSING_TENANT = "AUTH_005"  # Missing tenant claim in JWT
    AUTH_INVALID_REDIRECT = "AUTH_006"  # Invalid redirect URI

    # System Errors (SYS_001 - SYS_999)
    SYS_DATABASE_UNREACHABLE = "SYS_001"  # Database unreachable
    SYS_SECRETS_UNAVAILABLE = "SYS_002"  # Secrets Manager unavailable
    SYS_INTERNAL_ERROR = "SYS_003"  # Internal server error (unexpected exception)

    # Validation Errors (VAL_001 - VAL_999)
    VAL_INVALID_INPUT = "VAL_001"  # Invalid input data
    VAL_MISSING_FIELD = "VAL_002"  # Required field missing
    VAL_INVALID_FORMAT = "VAL_003"  # Invalid data format


# Error code descriptions for documentation and debugging
ERROR_DESCRIPTIONS: Dict[str, str] = {
    # Authentication Errors
    ErrorCode.AUTH_INVALID_TOKEN: "Invalid authentication token",
    ErrorCode.AUTH_CSRF_FAILED: "CSRF token validation failed",
    ErrorCode.AUTH_TOKEN_EXPIRED: "Authentication token has expired",
    ErrorCode.AUTH_INVALID_SIGNATURE: "Invalid token signature",
    ErrorCode.AUTH_MISSING_TENANT: "Missing tenant claim in JWT token",
    ErrorCode.AUTH_INVALID_REDIRECT: "Invalid redirect URI",

    # System Errors
    ErrorCode.SYS_DATABASE_UNREACHABLE: "Database connection unavailable",
    ErrorCode.SYS_SECRETS_UNAVAILABLE: "Secrets Manager unavailable",
    ErrorCode.SYS_INTERNAL_ERROR: "An unexpected error occurred",

    # Validation Errors
    ErrorCode.VAL_INVALID_INPUT: "Invalid input data provided",
    ErrorCode.VAL_MISSING_FIELD: "Required field is missing",
    ErrorCode.VAL_INVALID_FORMAT: "Invalid data format",
}


# Error code to HTTP status code mapping
ERROR_STATUS_CODES: Dict[str, int] = {
    # Authentication Errors -> 401 Unauthorized or 403 Forbidden
    ErrorCode.AUTH_INVALID_TOKEN: 401,
    ErrorCode.AUTH_CSRF_FAILED: 403,
    ErrorCode.AUTH_TOKEN_EXPIRED: 401,
    ErrorCode.AUTH_INVALID_SIGNATURE: 401,
    ErrorCode.AUTH_MISSING_TENANT: 403,
    ErrorCode.AUTH_INVALID_REDIRECT: 400,

    # System Errors -> 503 Service Unavailable or 500 Internal Server Error
    ErrorCode.SYS_DATABASE_UNREACHABLE: 503,
    ErrorCode.SYS_SECRETS_UNAVAILABLE: 503,
    ErrorCode.SYS_INTERNAL_ERROR: 500,

    # Validation Errors -> 400 Bad Request
    ErrorCode.VAL_INVALID_INPUT: 400,
    ErrorCode.VAL_MISSING_FIELD: 400,
    ErrorCode.VAL_INVALID_FORMAT: 400,
}


class APIException(Exception):
    """
    Base exception class for all API errors.

    This exception includes an error code, message, optional detail,
    and HTTP status code for standardized error responses.
    """

    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        """
        Initialize API exception.

        Args:
            error_code: Error code from ErrorCode enum
            message: User-friendly error message (defaults to description from registry)
            detail: Technical detail for debugging (not exposed to client in production)
            status_code: HTTP status code (defaults to mapping from ERROR_STATUS_CODES)
        """
        self.error_code = error_code
        self.message = message or ERROR_DESCRIPTIONS.get(error_code, "An error occurred")
        self.detail = detail
        self.status_code = status_code or ERROR_STATUS_CODES.get(error_code, 500)

        super().__init__(self.message)

    def to_dict(self, include_detail: bool = True) -> Dict[str, Any]:
        """
        Convert exception to dictionary for JSON response.

        Args:
            include_detail: Whether to include technical detail (False in production)

        Returns:
            Dictionary with error information
        """
        error_dict = {
            "code": self.error_code,
            "message": self.message,
        }

        if include_detail and self.detail:
            error_dict["detail"] = self.detail

        return error_dict


class AuthenticationError(APIException):
    """Exception for authentication failures (401 Unauthorized)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.AUTH_INVALID_TOKEN,
        message: Optional[str] = None,
        detail: Optional[str] = None,
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            detail=detail,
            status_code=401,
        )


class AuthorizationError(APIException):
    """Exception for authorization failures (403 Forbidden)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.AUTH_MISSING_TENANT,
        message: Optional[str] = None,
        detail: Optional[str] = None,
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            detail=detail,
            status_code=403,
        )


class ValidationError(APIException):
    """Exception for input validation failures (400 Bad Request)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.VAL_INVALID_INPUT,
        message: Optional[str] = None,
        detail: Optional[str] = None,
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            detail=detail,
            status_code=400,
        )


class SystemError(APIException):
    """Exception for system and infrastructure failures (500/503)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.SYS_INTERNAL_ERROR,
        message: Optional[str] = None,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            detail=detail,
            status_code=status_code,
        )


def format_error_response(
    error_code: str,
    message: str,
    detail: Optional[str] = None,
    request_id: Optional[str] = None,
    include_detail: bool = False,
) -> Dict[str, Any]:
    """
    Format standardized error response.

    Returns error response in the format:
    {
        "error": {
            "code": "AUTH_001",
            "message": "Invalid authentication token",
            "detail": "Token signature verification failed",  # Only if include_detail=True
            "request_id": "req-123-abc-456"
        }
    }

    Args:
        error_code: Error code string
        message: User-friendly error message
        detail: Technical detail for debugging (only included if include_detail=True)
        request_id: Request ID for correlation with logs
        include_detail: Whether to include technical detail (False in production)

    Returns:
        Dictionary with standardized error format
    """
    error_dict: Dict[str, Any] = {
        "code": error_code,
        "message": message,
    }

    # Only include detail if explicitly requested (e.g., development environment)
    if include_detail and detail:
        error_dict["detail"] = detail

    # Include request_id for correlation with server logs
    if request_id:
        error_dict["request_id"] = request_id

    return {"error": error_dict}
