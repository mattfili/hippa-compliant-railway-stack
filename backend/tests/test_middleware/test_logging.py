"""
Tests for logging middleware.

Covers critical workflows:
- Request ID generation and injection
- Structured logging with context
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.logging import LoggingMiddleware


def test_request_id_generated_and_added_to_response():
    """Test request ID is generated and added to response headers."""
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_sensitive_query_params_sanitized():
    """Test sensitive query parameters are sanitized in logs."""
    middleware = LoggingMiddleware(app=FastAPI())

    # Test sensitive parameter redaction
    params = {
        "patient_id": "12345",
        "name": "John Doe",
        "safe_param": "value",
    }

    sanitized = middleware._sanitize_query_params(params)

    assert sanitized["patient_id"] == "***"
    assert sanitized["safe_param"] == "value"
    assert sanitized["name"] == "John Doe"  # Not in SENSITIVE_PARAMS list
