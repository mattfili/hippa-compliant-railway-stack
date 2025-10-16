"""
Tests for JWT validation with JWKS caching.

Covers critical workflows:
- JWT signature verification
- Token expiration validation
- Issuer validation
- Tenant claim extraction
- JWKS key fetching and caching
"""

import time
from unittest.mock import AsyncMock, patch, Mock

import pytest
from jose import jwt

from app.auth.jwt_validator import (
    JWTValidator,
    TokenExpiredError,
    TokenSignatureError,
    TokenInvalidClaimError,
)
from app.auth.jwks_cache import JWKSCache


@pytest.mark.asyncio
async def test_validate_token_success(mock_jwks_cache, valid_jwt_claims):
    """Test successful JWT token validation with valid signature and claims."""
    # Mock signing key retrieval
    mock_signing_key = Mock()
    mock_jwks_cache.get_signing_key = AsyncMock(return_value=mock_signing_key)

    # Create validator
    validator = JWTValidator(
        issuer_url="https://test-issuer.example.com",
        client_id="test-client-id",
        jwks_cache=mock_jwks_cache,
    )

    # Create a real JWT token that jose can decode
    token = jwt.encode(valid_jwt_claims, "test-secret", algorithm="HS256")

    # Mock jwt.decode to return our claims
    with patch("app.auth.jwt_validator.jwt.decode", return_value=valid_jwt_claims):
        with patch("app.auth.jwt_validator.jwt.get_unverified_headers", return_value={"kid": "test-key-1"}):
            claims = await validator.validate_token(token)

            assert claims["sub"] == "user-123"
            assert claims["tenant_id"] == "org-456"
            mock_jwks_cache.get_signing_key.assert_called_once_with("test-key-1")


@pytest.mark.asyncio
async def test_validate_token_expired(mock_jwks_cache, expired_jwt_claims):
    """Test JWT validation fails with expired token."""
    mock_signing_key = Mock()
    mock_jwks_cache.get_signing_key = AsyncMock(return_value=mock_signing_key)

    validator = JWTValidator(
        issuer_url="https://test-issuer.example.com",
        client_id="test-client-id",
        jwks_cache=mock_jwks_cache,
    )

    token = jwt.encode(expired_jwt_claims, "test-secret", algorithm="HS256")

    # Mock jwt.decode to raise ExpiredSignatureError
    with patch("app.auth.jwt_validator.jwt.decode", side_effect=jwt.ExpiredSignatureError("Token expired")):
        with patch("app.auth.jwt_validator.jwt.get_unverified_headers", return_value={"kid": "test-key-1"}):
            with pytest.raises(TokenExpiredError, match="JWT token has expired"):
                await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_token_invalid_signature(mock_jwks_cache):
    """Test JWT validation fails with invalid signature."""
    mock_signing_key = Mock()
    mock_jwks_cache.get_signing_key = AsyncMock(return_value=mock_signing_key)

    validator = JWTValidator(
        issuer_url="https://test-issuer.example.com",
        client_id="test-client-id",
        jwks_cache=mock_jwks_cache,
    )

    # Mock jwt.decode to raise JWTError for signature verification failure
    with patch("app.auth.jwt_validator.jwt.decode", side_effect=jwt.JWTError("Signature verification failed")):
        with patch("app.auth.jwt_validator.jwt.get_unverified_headers", return_value={"kid": "test-key-1"}):
            with pytest.raises(TokenSignatureError, match="JWT signature verification failed"):
                await validator.validate_token("invalid.token.here")


@pytest.mark.asyncio
async def test_validate_token_invalid_issuer(mock_jwks_cache, valid_jwt_claims):
    """Test JWT validation fails with wrong issuer."""
    mock_signing_key = Mock()
    mock_jwks_cache.get_signing_key = AsyncMock(return_value=mock_signing_key)

    validator = JWTValidator(
        issuer_url="https://test-issuer.example.com",
        client_id="test-client-id",
        jwks_cache=mock_jwks_cache,
    )

    # Mock jwt.decode to raise JWTClaimsError for issuer mismatch
    with patch("app.auth.jwt_validator.jwt.decode", side_effect=jwt.JWTClaimsError("Invalid issuer")):
        with patch("app.auth.jwt_validator.jwt.get_unverified_headers", return_value={"kid": "test-key-1"}):
            with pytest.raises(TokenInvalidClaimError, match="Invalid JWT claims"):
                await validator.validate_token("token.with.wrong.issuer")


@pytest.mark.asyncio
async def test_validate_token_exceeds_max_lifetime(mock_jwks_cache):
    """Test JWT validation fails when token lifetime exceeds maximum."""
    mock_signing_key = Mock()
    mock_jwks_cache.get_signing_key = AsyncMock(return_value=mock_signing_key)

    validator = JWTValidator(
        issuer_url="https://test-issuer.example.com",
        client_id="test-client-id",
        jwks_cache=mock_jwks_cache,
        max_lifetime_minutes=60,
    )

    # Create claims with 90-minute lifetime (exceeds 60-minute max)
    current_time = int(time.time())
    long_lived_claims = {
        "sub": "user-123",
        "tenant_id": "org-456",
        "iss": "https://test-issuer.example.com",
        "aud": "test-client-id",
        "iat": current_time,
        "exp": current_time + 5400,  # 90 minutes
    }

    token = jwt.encode(long_lived_claims, "test-secret", algorithm="HS256")

    with patch("app.auth.jwt_validator.jwt.decode", return_value=long_lived_claims):
        with patch("app.auth.jwt_validator.jwt.get_unverified_headers", return_value={"kid": "test-key-1"}):
            with pytest.raises(TokenInvalidClaimError, match="Token lifetime exceeds maximum"):
                await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_token_missing_kid(mock_jwks_cache):
    """Test JWT validation fails when token header is missing kid."""
    validator = JWTValidator(
        issuer_url="https://test-issuer.example.com",
        client_id="test-client-id",
        jwks_cache=mock_jwks_cache,
    )

    # Mock missing kid in header
    with patch("app.auth.jwt_validator.jwt.get_unverified_headers", return_value={}):
        with pytest.raises(TokenInvalidClaimError, match="JWT token missing 'kid' in header"):
            await validator.validate_token("token.without.kid")


@pytest.mark.asyncio
async def test_extract_user_id_success(mock_jwks_cache, valid_jwt_claims):
    """Test extracting user ID from JWT claims."""
    validator = JWTValidator(
        issuer_url="https://test-issuer.example.com",
        client_id="test-client-id",
        jwks_cache=mock_jwks_cache,
    )

    user_id = validator.extract_user_id(valid_jwt_claims)
    assert user_id == "user-123"


@pytest.mark.asyncio
async def test_extract_user_id_missing_sub(mock_jwks_cache):
    """Test extracting user ID fails when sub claim is missing."""
    validator = JWTValidator(
        issuer_url="https://test-issuer.example.com",
        client_id="test-client-id",
        jwks_cache=mock_jwks_cache,
    )

    claims_without_sub = {"tenant_id": "org-456"}

    with pytest.raises(TokenInvalidClaimError, match="JWT token missing 'sub' \\(user ID\\) claim"):
        validator.extract_user_id(claims_without_sub)
