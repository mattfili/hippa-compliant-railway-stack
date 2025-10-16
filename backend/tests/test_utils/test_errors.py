"""Tests for error handling utilities."""

import pytest
from app.utils.errors import (
    ErrorCode,
    APIException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    SystemError,
    format_error_response,
)


def test_error_codes_defined():
    """Test that all error codes are properly defined."""
    assert ErrorCode.AUTH_INVALID_TOKEN == "AUTH_001"
    assert ErrorCode.AUTH_CSRF_FAILED == "AUTH_002"
    assert ErrorCode.AUTH_TOKEN_EXPIRED == "AUTH_003"
    assert ErrorCode.AUTH_INVALID_SIGNATURE == "AUTH_004"
    assert ErrorCode.AUTH_MISSING_TENANT == "AUTH_005"
    assert ErrorCode.AUTH_INVALID_REDIRECT == "AUTH_006"
    assert ErrorCode.SYS_DATABASE_UNREACHABLE == "SYS_001"
    assert ErrorCode.SYS_SECRETS_UNAVAILABLE == "SYS_002"
    assert ErrorCode.SYS_INTERNAL_ERROR == "SYS_003"
    assert ErrorCode.VAL_INVALID_INPUT == "VAL_001"
    assert ErrorCode.VAL_MISSING_FIELD == "VAL_002"
    assert ErrorCode.VAL_INVALID_FORMAT == "VAL_003"


def test_api_exception_creation():
    """Test APIException class initialization."""
    exc = APIException(
        error_code=ErrorCode.AUTH_INVALID_TOKEN,
        message="Test error message",
        detail="Test error detail",
    )
    assert exc.error_code == ErrorCode.AUTH_INVALID_TOKEN
    assert exc.message == "Test error message"
    assert exc.detail == "Test error detail"
    assert exc.status_code == 401


def test_api_exception_to_dict():
    """Test APIException to_dict method."""
    exc = APIException(
        error_code=ErrorCode.AUTH_INVALID_TOKEN,
        message="Test error",
        detail="Test detail",
    )
    error_dict = exc.to_dict()
    assert error_dict["code"] == ErrorCode.AUTH_INVALID_TOKEN
    assert error_dict["message"] == "Test error"
    assert error_dict["detail"] == "Test detail"


def test_authentication_error():
    """Test AuthenticationError exception class."""
    exc = AuthenticationError()
    assert exc.status_code == 401
    assert exc.error_code.startswith("AUTH_")


def test_authorization_error():
    """Test AuthorizationError exception class."""
    exc = AuthorizationError()
    assert exc.status_code == 403
    assert exc.error_code.startswith("AUTH_")


def test_validation_error():
    """Test ValidationError exception class."""
    exc = ValidationError()
    assert exc.status_code == 400
    assert exc.error_code.startswith("VAL_")


def test_system_error():
    """Test SystemError exception class."""
    exc = SystemError()
    assert exc.status_code == 500
    assert exc.error_code.startswith("SYS_")


def test_format_error_response_with_detail():
    """Test error response formatter with detail included."""
    response = format_error_response(
        error_code="AUTH_001",
        message="Test error message",
        detail="Test error detail",
        request_id="req-12345",
        include_detail=True,
    )

    assert response["error"]["code"] == "AUTH_001"
    assert response["error"]["message"] == "Test error message"
    assert response["error"]["detail"] == "Test error detail"
    assert response["error"]["request_id"] == "req-12345"


def test_format_error_response_without_detail():
    """Test error response formatter without detail."""
    response = format_error_response(
        error_code="AUTH_001",
        message="Test error message",
        detail="Test error detail that should not be included",
        include_detail=False,
    )

    assert response["error"]["code"] == "AUTH_001"
    assert response["error"]["message"] == "Test error message"
    assert "detail" not in response["error"]


def test_format_error_response_without_request_id():
    """Test error response formatter without request_id."""
    response = format_error_response(
        error_code="AUTH_001",
        message="Test error message",
    )

    assert response["error"]["code"] == "AUTH_001"
    assert response["error"]["message"] == "Test error message"
    assert "request_id" not in response["error"]
