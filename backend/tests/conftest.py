"""
Pytest configuration and reusable fixtures for testing.

Provides:
- Mock JWT tokens with valid/expired/invalid scenarios
- Mock JWKS endpoint responses
- Mock database sessions
- Test FastAPI client
"""

import os
import time
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

# Set required environment variables before importing app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("OIDC_ISSUER_URL", "https://test-issuer.example.com")
os.environ.setdefault("OIDC_CLIENT_ID", "test-client-id")
os.environ.setdefault("OIDC_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("ENVIRONMENT", "development")  # Must be development, staging, or production
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.oidc_issuer_url = "https://test-issuer.example.com"
    settings.oidc_client_id = "test-client-id"
    settings.oidc_client_secret = "test-client-secret"
    settings.jwt_tenant_claim_name = "tenant_id"
    settings.jwt_max_lifetime_minutes = 60
    settings.jwks_cache_ttl_seconds = 3600
    settings.get_allowed_origins_list = Mock(return_value=["http://localhost:3000"])
    return settings


@pytest.fixture
def valid_jwt_claims() -> Dict[str, Any]:
    """Generate valid JWT claims for testing."""
    current_time = int(time.time())
    return {
        "sub": "user-123",
        "tenant_id": "org-456",
        "iss": "https://test-issuer.example.com",
        "aud": "test-client-id",
        "iat": current_time,
        "exp": current_time + 3600,
        "email": "user@example.com",
    }


@pytest.fixture
def expired_jwt_claims() -> Dict[str, Any]:
    """Generate expired JWT claims for testing."""
    current_time = int(time.time())
    return {
        "sub": "user-123",
        "tenant_id": "org-456",
        "iss": "https://test-issuer.example.com",
        "aud": "test-client-id",
        "iat": current_time - 7200,  # Issued 2 hours ago
        "exp": current_time - 3600,  # Expired 1 hour ago
        "email": "user@example.com",
    }


@pytest.fixture
def missing_tenant_claims() -> Dict[str, Any]:
    """Generate JWT claims without tenant_id for testing."""
    current_time = int(time.time())
    return {
        "sub": "user-123",
        "iss": "https://test-issuer.example.com",
        "aud": "test-client-id",
        "iat": current_time,
        "exp": current_time + 3600,
        "email": "user@example.com",
    }


@pytest.fixture
def mock_jwks_response():
    """Mock JWKS endpoint response."""
    return {
        "keys": [
            {
                "kid": "test-key-1",
                "kty": "RSA",
                "use": "sig",
                "n": "test-modulus",
                "e": "AQAB",
                "alg": "RS256",
            }
        ]
    }


@pytest.fixture
def mock_signing_key():
    """Mock RSA signing key for JWT validation."""
    key = Mock()
    key.to_pem = Mock(return_value=b"mock-pem-key")
    return key


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_database_engine():
    """Mock database engine for health checks."""
    engine = Mock()

    # Mock async context manager for connection
    connection = AsyncMock()
    connection.execute = AsyncMock()

    # Mock async context manager for connect
    connect_context = AsyncMock()
    connect_context.__aenter__ = AsyncMock(return_value=connection)
    connect_context.__aexit__ = AsyncMock(return_value=None)

    engine.connect = Mock(return_value=connect_context)

    return engine


@pytest.fixture
def mock_jwks_cache():
    """Mock JWKS cache for testing."""
    cache = AsyncMock()
    cache.get_signing_key = AsyncMock()
    cache.get_key = AsyncMock()
    return cache


@pytest.fixture
def mock_jwt_validator(mock_jwks_cache):
    """Mock JWT validator for testing."""
    from app.auth.jwt_validator import JWTValidator

    validator = Mock(spec=JWTValidator)
    validator.validate_token = AsyncMock()
    validator.extract_user_id = Mock()
    validator.jwks_cache = mock_jwks_cache
    return validator


@pytest.fixture
def mock_tenant_extractor():
    """Mock tenant extractor for testing."""
    from app.auth.tenant_extractor import TenantExtractor

    extractor = Mock(spec=TenantExtractor)
    extractor.extract_tenant_id = Mock()
    return extractor


def create_test_jwt(claims: Dict[str, Any], key: str = "test-secret") -> str:
    """
    Create a test JWT token for testing.

    Note: This uses HS256 for simplicity in tests. Real tokens use RS256.

    Args:
        claims: JWT claims dictionary
        key: Secret key for signing (default: "test-secret")

    Returns:
        str: Encoded JWT token
    """
    return jwt.encode(claims, key, algorithm="HS256")


@pytest.fixture
def valid_test_token(valid_jwt_claims) -> str:
    """Generate valid test JWT token."""
    return create_test_jwt(valid_jwt_claims)


@pytest.fixture
def expired_test_token(expired_jwt_claims) -> str:
    """Generate expired test JWT token."""
    return create_test_jwt(expired_jwt_claims)


@pytest.fixture
def missing_tenant_token(missing_tenant_claims) -> str:
    """Generate test JWT token without tenant claim."""
    return create_test_jwt(missing_tenant_claims)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for external API calls."""
    client = AsyncMock()
    response = AsyncMock()
    response.status_code = 200
    response.json = Mock(return_value={"access_token": "mock-token", "expires_in": 3600})
    response.text = "mock response"
    client.post = AsyncMock(return_value=response)
    client.get = AsyncMock(return_value=response)
    return client
