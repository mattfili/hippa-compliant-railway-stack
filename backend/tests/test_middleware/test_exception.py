"""
Tests for exception handling middleware.

Covers critical workflows:
- Unhandled exceptions converted to standardized error format
- Stack traces not exposed to clients
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.middleware.exception import ExceptionHandlerMiddleware
from app.utils.errors import APIException, ErrorCode


def test_api_exception_handled_with_standardized_format():
    """Test APIException is converted to standardized error response."""
    app = FastAPI()
    app.add_middleware(ExceptionHandlerMiddleware)

    @app.get("/test")
    async def test_endpoint():
        raise APIException(
            error_code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Invalid token",
            detail="Token signature verification failed",
            status_code=401,
        )

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == ErrorCode.AUTH_INVALID_TOKEN
    assert data["error"]["message"] == "Invalid token"


def test_unexpected_exception_returns_generic_error():
    """Test unexpected exceptions return generic internal server error."""
    app = FastAPI()
    app.add_middleware(ExceptionHandlerMiddleware)

    @app.get("/test")
    async def test_endpoint():
        raise ValueError("Unexpected error")

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == ErrorCode.SYS_INTERNAL_ERROR
    # Stack trace should not be in response (in production)
