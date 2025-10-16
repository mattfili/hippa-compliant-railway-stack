"""
FastAPI dependencies for authentication and authorization.

This module provides:
- JWT token extraction from Authorization header
- Token validation using JWTValidator
- Tenant ID extraction from JWT claims
- User context injection for downstream handlers
"""

import logging
from typing import Annotated, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.auth.jwks_cache import JWKSCache
from app.auth.jwt_validator import (
    JWTValidator,
    JWTValidationError,
    TokenExpiredError,
    TokenSignatureError,
    TokenInvalidClaimError,
)
from app.auth.tenant_extractor import (
    TenantExtractor,
    MissingTenantClaimError,
    InvalidTenantFormatError,
)

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme for OpenAPI docs
security = HTTPBearer(
    scheme_name="Bearer",
    description="JWT token from OIDC/SAML identity provider",
)


class UserContext:
    """
    User context extracted from authenticated JWT token.

    Contains user_id, tenant_id, and full JWT claims for downstream use.
    """

    def __init__(self, user_id: str, tenant_id: str, claims: Dict[str, Any]):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.claims = claims

    def __repr__(self) -> str:
        return f"UserContext(user_id={self.user_id}, tenant_id={self.tenant_id})"


# Global instances (initialized on first use)
_jwks_cache: JWKSCache | None = None
_jwt_validator: JWTValidator | None = None
_tenant_extractor: TenantExtractor | None = None


def get_jwks_cache() -> JWKSCache:
    """
    Get or create JWKS cache singleton.

    Returns:
        JWKSCache: Shared JWKS cache instance
    """
    global _jwks_cache

    if _jwks_cache is None:
        settings = get_settings()

        # Construct JWKS URL from issuer
        issuer_url = str(settings.oidc_issuer_url).rstrip("/")
        jwks_url = f"{issuer_url}/.well-known/jwks.json"

        _jwks_cache = JWKSCache(
            jwks_url=jwks_url,
            ttl_seconds=settings.jwks_cache_ttl_seconds,
        )

        # Start background refresh task
        _jwks_cache.start_background_refresh()

        logger.info(f"Initialized JWKS cache with URL: {jwks_url}")

    return _jwks_cache


def get_jwt_validator(
    jwks_cache: Annotated[JWKSCache, Depends(get_jwks_cache)]
) -> JWTValidator:
    """
    Get or create JWT validator singleton.

    Args:
        jwks_cache: JWKS cache dependency

    Returns:
        JWTValidator: Shared JWT validator instance
    """
    global _jwt_validator

    if _jwt_validator is None:
        settings = get_settings()

        _jwt_validator = JWTValidator(
            issuer_url=settings.oidc_issuer_url,
            client_id=settings.oidc_client_id,
            jwks_cache=jwks_cache,
            max_lifetime_minutes=settings.jwt_max_lifetime_minutes,
        )

        logger.info("Initialized JWT validator")

    return _jwt_validator


def get_tenant_extractor() -> TenantExtractor:
    """
    Get or create tenant extractor singleton.

    Returns:
        TenantExtractor: Shared tenant extractor instance
    """
    global _tenant_extractor

    if _tenant_extractor is None:
        settings = get_settings()

        _tenant_extractor = TenantExtractor(
            claim_names=[settings.jwt_tenant_claim_name],
        )

        logger.info(
            f"Initialized tenant extractor with claim name: {settings.jwt_tenant_claim_name}"
        )

    return _tenant_extractor


async def get_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> str:
    """
    Extract JWT token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        str: JWT token string

    Raises:
        HTTPException: If Authorization header is missing or invalid
    """
    if not credentials or not credentials.credentials:
        logger.warning("Request missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_001",
                    "message": "Missing or invalid Authorization header",
                    "detail": "Request must include Authorization: Bearer <token> header",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


async def get_current_user(
    token: Annotated[str, Depends(get_token)],
    validator: Annotated[JWTValidator, Depends(get_jwt_validator)],
    tenant_extractor: Annotated[TenantExtractor, Depends(get_tenant_extractor)],
) -> UserContext:
    """
    Validate JWT token and extract user context.

    This dependency:
    1. Validates JWT signature using JWKS keys
    2. Validates JWT claims (exp, iat, iss, aud)
    3. Extracts user_id from 'sub' claim
    4. Extracts tenant_id from configured claim name
    5. Returns UserContext with user_id, tenant_id, and claims

    Args:
        token: JWT token from Authorization header
        validator: JWT validator dependency
        tenant_extractor: Tenant extractor dependency

    Returns:
        UserContext: Authenticated user context

    Raises:
        HTTPException: If authentication fails (401) or tenant claim is missing (403)
    """
    try:
        # Validate JWT token
        claims = await validator.validate_token(token)

        # Extract user ID
        user_id = validator.extract_user_id(claims)

        # Extract tenant ID
        try:
            tenant_id = tenant_extractor.extract_tenant_id(claims)
        except MissingTenantClaimError as e:
            logger.warning(f"Tenant claim missing for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "AUTH_005",
                        "message": "Missing tenant claim in JWT token",
                        "detail": str(e),
                    }
                },
            ) from e
        except InvalidTenantFormatError as e:
            logger.warning(f"Invalid tenant ID format for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "AUTH_007",
                        "message": "Invalid tenant ID format",
                        "detail": str(e),
                    }
                },
            ) from e

        logger.info(f"User authenticated: {user_id} (tenant: {tenant_id})")

        return UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            claims=claims,
        )

    except TokenExpiredError as e:
        logger.warning(f"Token expired: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_003",
                    "message": "JWT token has expired",
                    "detail": "Please authenticate again to obtain a new token",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except TokenSignatureError as e:
        logger.warning(f"Token signature verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_004",
                    "message": "Invalid JWT token signature",
                    "detail": "Token signature verification failed",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except TokenInvalidClaimError as e:
        logger.warning(f"Invalid JWT claims: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_001",
                    "message": "Invalid JWT token claims",
                    "detail": str(e),
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except JWTValidationError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_001",
                    "message": "JWT token validation failed",
                    "detail": str(e),
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "SYS_003",
                    "message": "Internal server error during authentication",
                    "detail": "An unexpected error occurred. Please try again.",
                }
            },
        ) from e


# Type annotation for dependency injection
CurrentUser = Annotated[UserContext, Depends(get_current_user)]
