"""
Tests for health check API endpoints.

Covers critical workflows:
- Liveness probe (always returns OK)
- Readiness probe with database check
- Health checks don't require authentication
"""

from unittest.mock import patch, AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def health_test_client():
    """Create test client for health endpoints."""
    return TestClient(app)


def test_liveness_probe_returns_ok(health_test_client):
    """Test liveness probe always returns 200 OK."""
    response = health_test_client.get("/api/v1/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert isinstance(data["timestamp"], int)


def test_readiness_probe_database_available(health_test_client, mock_database_engine):
    """Test readiness probe returns 200 when database is available."""
    with patch("app.api.v1.health.get_engine", return_value=mock_database_engine):
        response = health_test_client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "ok"
        assert "latency_ms" in data["checks"]["database"]
        assert "timestamp" in data


def test_readiness_probe_database_unavailable(health_test_client):
    """Test readiness probe returns 503 when database is unavailable."""
    # Mock database engine that raises connection error
    mock_engine = Mock()
    mock_connection = AsyncMock()
    mock_connection.execute = AsyncMock(side_effect=Exception("Database connection failed"))

    connect_context = AsyncMock()
    connect_context.__aenter__ = AsyncMock(return_value=mock_connection)
    connect_context.__aexit__ = AsyncMock(return_value=None)

    mock_engine.connect = Mock(return_value=connect_context)

    with patch("app.api.v1.health.get_engine", return_value=mock_engine):
        response = health_test_client.get("/api/v1/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["checks"]["database"]["status"] == "unavailable"
        assert data["checks"]["database"]["error"] is not None


def test_health_endpoints_no_authentication_required(health_test_client):
    """Test health endpoints don't require authentication."""
    # Test liveness without auth
    response = health_test_client.get("/api/v1/health/live")
    assert response.status_code == 200

    # Test readiness without auth (mock database to avoid engine error)
    mock_engine = Mock()
    mock_connection = AsyncMock()
    mock_connection.execute = AsyncMock()

    connect_context = AsyncMock()
    connect_context.__aenter__ = AsyncMock(return_value=mock_connection)
    connect_context.__aexit__ = AsyncMock(return_value=None)

    mock_engine.connect = Mock(return_value=connect_context)

    with patch("app.api.v1.health.get_engine", return_value=mock_engine):
        response = health_test_client.get("/api/v1/health/ready")
        assert response.status_code == 200
