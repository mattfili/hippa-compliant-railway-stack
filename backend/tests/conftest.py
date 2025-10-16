"""
Pytest configuration and reusable fixtures for testing.

Provides:
- Mock JWT tokens with valid/expired/invalid scenarios
- Mock JWKS endpoint responses
- Mock database sessions
- Test FastAPI client
- Audit log test fixtures
"""

import os
import time
import uuid
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
import pytest_asyncio
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, event, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Mapped, mapped_column

from app.main import app
from app.database.base import Base, SoftDeleteMixin


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


# Database fixtures for model testing
@pytest_asyncio.fixture
async def test_engine():
    """
    Create an in-memory SQLite database engine for testing.

    Uses StaticPool to maintain the same connection across tests.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    Create a database session for testing.

    Automatically rolls back changes after each test.
    """
    # Create session factory
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create session
    async with async_session_factory() as session:
        yield session
        # Rollback after test
        await session.rollback()


# Audit log test fixtures using real models
@pytest_asyncio.fixture
async def test_tenant(db_session):
    """Create a test tenant for audit log testing."""
    from app.models.tenant import Tenant

    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Test Tenant 1",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def test_tenant2(db_session):
    """Create a second test tenant for multi-tenant testing."""
    from app.models.tenant import Tenant

    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Test Tenant 2",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant):
    """Create a test user for audit log testing."""
    from app.models.user import User

    user = User(
        id=str(uuid.uuid4()),
        tenant_id=test_tenant.id,
        email="user1@test.com",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_user2(db_session, test_tenant2):
    """Create a second test user for multi-tenant testing."""
    from app.models.user import User

    user = User(
        id=str(uuid.uuid4()),
        tenant_id=test_tenant2.id,
        email="user2@test.com",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def audit_log_count_validator(db_session):
    """
    Fixture to verify audit log record count doesn't decrease.

    Returns a function that can be called to get current count and
    verify it only increases (never decreases).
    """
    from app.models.audit_log import AuditLog
    from sqlalchemy import select, func

    async def get_count():
        """Get current audit log count."""
        result = await db_session.execute(select(func.count()).select_from(AuditLog))
        return result.scalar()

    # Store initial count
    initial_count = await get_count()

    class CountValidator:
        """Helper class to validate audit log count."""

        def __init__(self):
            self.last_count = initial_count

        async def verify_count_increased(self, expected_increase: int = 1):
            """Verify count increased by expected amount."""
            current_count = await get_count()
            assert current_count == self.last_count + expected_increase, (
                f"Expected count to increase by {expected_increase}, "
                f"but went from {self.last_count} to {current_count}"
            )
            self.last_count = current_count

        async def verify_count_unchanged(self):
            """Verify count did not change."""
            current_count = await get_count()
            assert current_count == self.last_count, (
                f"Expected count to remain {self.last_count}, "
                f"but got {current_count}"
            )

    return CountValidator()

# RLS Testing Fixtures

@pytest_asyncio.fixture
async def test_tenants(db_session):
    """
    Create two test tenants for RLS testing.

    Returns:
        tuple: (tenant1_id, tenant2_id) as UUID strings
    """
    from sqlalchemy import text

    tenant1_id = str(uuid.uuid4())
    tenant2_id = str(uuid.uuid4())

    # Insert test tenants
    await db_session.execute(
        text("""
            INSERT INTO tenants (id, name, status, created_at, updated_at)
            VALUES
                (:tenant1_id, 'Test Tenant 1', 'active', NOW(), NOW()),
                (:tenant2_id, 'Test Tenant 2', 'active', NOW(), NOW())
        """),
        {"tenant1_id": tenant1_id, "tenant2_id": tenant2_id}
    )
    await db_session.commit()

    return tenant1_id, tenant2_id


@pytest_asyncio.fixture
async def test_users(db_session, test_tenants):
    """
    Create test users for each test tenant.

    Args:
        db_session: Database session
        test_tenants: Fixture providing tenant IDs

    Returns:
        tuple: (user1_id, user2_id) as UUID strings for tenant1 and tenant2
    """
    from sqlalchemy import text

    tenant1_id, tenant2_id = test_tenants

    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())

    # Insert test users for both tenants
    await db_session.execute(
        text("""
            INSERT INTO users (id, tenant_id, email, full_name, created_at, updated_at)
            VALUES
                (:user1_id, :tenant1_id, 'user1@tenant1.com', 'User 1', NOW(), NOW()),
                (:user2_id, :tenant2_id, 'user2@tenant2.com', 'User 2', NOW(), NOW())
        """),
        {
            "user1_id": user1_id,
            "tenant1_id": tenant1_id,
            "user2_id": user2_id,
            "tenant2_id": tenant2_id
        }
    )
    await db_session.commit()

    return user1_id, user2_id


@pytest_asyncio.fixture
async def set_tenant_context(db_session):
    """
    Fixture factory for setting tenant context in RLS tests.

    Returns a function that sets the app.current_tenant_id session variable.

    Usage:
        await set_tenant_context(tenant_id)
    """
    from sqlalchemy import text

    async def _set_context(tenant_id: str):
        """
        Set the tenant context for RLS policies.

        Args:
            tenant_id: UUID string of the tenant
        """
        await db_session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )

    return _set_context


@pytest_asyncio.fixture
async def clear_tenant_context(db_session):
    """
    Fixture for clearing tenant context in RLS tests.

    Returns a function that clears the app.current_tenant_id session variable.

    Usage:
        await clear_tenant_context()
    """
    from sqlalchemy import text

    async def _clear_context():
        """Clear the tenant context by setting it to empty string."""
        await db_session.execute(text("SET LOCAL app.current_tenant_id = ''"))

    return _clear_context
