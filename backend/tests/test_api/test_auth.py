"""
Tests for authentication API endpoints.

Covers critical workflows:
- Auth callback with code exchange
- Token validation endpoint
- Logout endpoint with redirect URI validation
"""

from unittest.mock import patch, AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def auth_test_client():
    """Create test client for auth endpoints."""
    return TestClient(app)


def test_auth_callback_success(auth_test_client, mock_httpx_client, mock_settings):
    """Test successful auth callback with valid authorization code."""
    # Mock httpx client for token exchange
    with patch("app.api.v1.auth.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_httpx_client
        mock_client_class.return_value.__aexit__.return_value = None

        with patch("app.api.v1.auth.get_settings", return_value=mock_settings):
            response = auth_test_client.post(
                "/api/v1/auth/callback",
                json={"code": "valid-auth-code", "state": "valid-csrf-state"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "mock-token"
            assert data["token_type"] == "Bearer"
            assert data["expires_in"] == 3600


def test_auth_callback_invalid_code(auth_test_client, mock_settings):
    """Test auth callback fails with invalid authorization code."""
    # Mock failed token exchange
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.text = "Invalid authorization code"
    mock_response.json = Mock(return_value={"error": "invalid_grant"})

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.api.v1.auth.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        with patch("app.api.v1.auth.get_settings", return_value=mock_settings):
            response = auth_test_client.post(
                "/api/v1/auth/callback",
                json={"code": "invalid-auth-code", "state": "valid-csrf-state"},
            )

            assert response.status_code == 400
            data = response.json()
            # Error is wrapped in "detail" by FastAPI HTTPException
            assert "detail" in data
            assert data["detail"]["error"]["code"] == "AUTH_001"


def test_validate_token_success(auth_test_client, valid_jwt_claims):
    """Test token validation with valid JWT."""
    from app.auth.dependencies import UserContext

    # Mock the get_current_user dependency to return a valid user
    user_context = UserContext(
        user_id="user-123",
        tenant_id="org-456",
        claims=valid_jwt_claims,
    )

    def override_get_current_user():
        return user_context

    from app.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = auth_test_client.get(
            "/api/v1/auth/validate",
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user_id"] == "user-123"
        assert data["tenant_id"] == "org-456"
        assert "expires_at" in data
    finally:
        app.dependency_overrides.clear()


def test_validate_token_missing_header(auth_test_client):
    """Test token validation fails without Authorization header."""
    response = auth_test_client.get("/api/v1/auth/validate")

    assert response.status_code == 403  # FastAPI returns 403 for missing auth


def test_validate_token_expired(auth_test_client):
    """Test token validation fails with expired token."""
    from app.auth.jwt_validator import TokenExpiredError
    from fastapi import HTTPException, status

    def override_get_current_user():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_003",
                    "message": "JWT token has expired",
                }
            },
        )

    from app.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = auth_test_client.get(
            "/api/v1/auth/validate",
            headers={"Authorization": "Bearer expired-token"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"]["code"] == "AUTH_003"
    finally:
        app.dependency_overrides.clear()


def test_validate_token_missing_tenant_claim(auth_test_client):
    """Test token validation fails when tenant claim is missing."""
    from fastapi import HTTPException, status

    def override_get_current_user():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "AUTH_005",
                    "message": "Missing tenant claim in JWT token",
                }
            },
        )

    from app.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = auth_test_client.get(
            "/api/v1/auth/validate",
            headers={"Authorization": "Bearer token-without-tenant"},
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"]["code"] == "AUTH_005"
    finally:
        app.dependency_overrides.clear()


def test_logout_valid_redirect_uri(auth_test_client, mock_settings):
    """Test logout with valid redirect URI returns IdP logout URL."""
    with patch("app.api.v1.auth.get_settings", return_value=mock_settings):
        response = auth_test_client.post(
            "/api/v1/auth/logout",
            json={"redirect_uri": "http://localhost:3000"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "logout_url" in data
        assert "test-issuer.example.com/logout" in data["logout_url"]
        assert "redirect_uri=" in data["logout_url"] or "logout_uri=" in data["logout_url"]


def test_logout_invalid_redirect_uri(auth_test_client, mock_settings):
    """Test logout fails with invalid redirect URI."""
    with patch("app.api.v1.auth.get_settings", return_value=mock_settings):
        response = auth_test_client.post(
            "/api/v1/auth/logout",
            json={"redirect_uri": "https://malicious-site.com"},
        )

        assert response.status_code == 400
        data = response.json()
        # Error is wrapped in "detail" by FastAPI HTTPException
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "AUTH_006"
        assert "Invalid redirect URI" in data["detail"]["error"]["message"]
