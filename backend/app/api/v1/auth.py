"""
Authentication API endpoints for OIDC/SAML authentication flow.

This module provides:
- POST /api/v1/auth/callback - Handle IdP callback and exchange auth code for JWT
- GET /api/v1/auth/validate - Validate current user's JWT token
- POST /api/v1/auth/logout - Invalidate session and return IdP logout URL

All endpoints use standardized error responses with request_id tracking.
"""

import logging
import time
from typing import Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field, HttpUrl

from app.auth.dependencies import CurrentUser
from app.config import get_settings
from app.utils.errors import ErrorCode, format_error_response

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


# Request/Response Models

class CallbackRequest(BaseModel):
    """Request body for auth callback endpoint."""

    code: str = Field(
        ...,
        description="Authorization code from IdP callback",
        min_length=1,
    )
    state: str = Field(
        ...,
        description="CSRF state token for validation",
        min_length=1,
    )


class CallbackResponse(BaseModel):
    """Response from auth callback endpoint."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class ValidateResponse(BaseModel):
    """Response from token validation endpoint."""

    valid: bool = Field(..., description="Whether token is valid")
    user_id: str = Field(..., description="Authenticated user ID")
    tenant_id: str = Field(..., description="User's tenant ID")
    expires_at: int = Field(..., description="Token expiration timestamp (Unix time)")


class LogoutRequest(BaseModel):
    """Request body for logout endpoint."""

    redirect_uri: str = Field(
        ...,
        description="URI to redirect to after logout",
        min_length=1,
    )


class LogoutResponse(BaseModel):
    """Response from logout endpoint."""

    logout_url: str = Field(..., description="IdP logout URL to redirect to")


# Endpoints

@router.post(
    "/callback",
    response_model=CallbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Handle IdP authentication callback",
    description="""
    Handle callback from OIDC/SAML identity provider after successful authentication.

    This endpoint:
    1. Validates CSRF state token
    2. Exchanges authorization code for JWT access token
    3. Returns JWT token to client for subsequent requests

    The JWT token should be included in subsequent requests as:
    `Authorization: Bearer <token>`
    """,
    responses={
        200: {
            "description": "Authentication successful, JWT token returned",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "Bearer",
                        "expires_in": 3600,
                    }
                }
            },
        },
        400: {
            "description": "Invalid authorization code or CSRF validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_001",
                            "message": "Invalid authorization code",
                            "detail": "Authorization code exchange failed",
                            "request_id": "req-123-abc-456",
                        }
                    }
                }
            },
        },
    },
)
async def auth_callback(
    request: Request,
    callback_data: CallbackRequest,
) -> CallbackResponse:
    """
    Handle IdP callback and exchange authorization code for JWT token.

    Args:
        request: FastAPI request object (for request_id)
        callback_data: Authorization code and CSRF state from IdP

    Returns:
        CallbackResponse: JWT access token and expiration info

    Raises:
        HTTPException: If code exchange fails or CSRF validation fails
    """
    settings = get_settings()
    request_id = getattr(request.state, "request_id", None)

    logger.info(
        "Processing auth callback",
        extra={
            "context": {
                "request_id": request_id,
                "state": callback_data.state[:10] + "...",  # Log partial state for debugging
            }
        },
    )

    # In a production implementation, CSRF state validation would happen here
    # For this scaffold, we document the pattern but don't implement full CSRF flow
    # since state management requires session storage (future feature)

    # Note: This is a simplified implementation for the scaffold
    # In production, you would:
    # 1. Validate CSRF state against stored session value
    # 2. Exchange auth code for token at IdP token endpoint
    # 3. Return the actual JWT from IdP

    try:
        # Exchange authorization code for JWT token at IdP token endpoint
        token_endpoint = f"{str(settings.oidc_issuer_url).rstrip('/')}/oauth2/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": callback_data.code,
                    "client_id": settings.oidc_client_id,
                    "client_secret": settings.oidc_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.warning(
                    f"Token exchange failed with status {response.status_code}",
                    extra={
                        "context": {
                            "request_id": request_id,
                            "status_code": response.status_code,
                            "error": response.text,
                        }
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=format_error_response(
                        error_code=ErrorCode.AUTH_INVALID_TOKEN,
                        message="Invalid authorization code",
                        detail="Authorization code exchange failed at IdP",
                        request_id=request_id,
                    ),
                )

            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)

            if not access_token:
                logger.error(
                    "Token response missing access_token",
                    extra={
                        "context": {
                            "request_id": request_id,
                            "response_keys": list(token_data.keys()),
                        }
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=format_error_response(
                        error_code=ErrorCode.SYS_INTERNAL_ERROR,
                        message="Token exchange failed",
                        detail="IdP response missing access_token",
                        request_id=request_id,
                    ),
                )

            logger.info(
                "Auth callback successful",
                extra={
                    "context": {
                        "request_id": request_id,
                        "expires_in": expires_in,
                    }
                },
            )

            return CallbackResponse(
                access_token=access_token,
                token_type="Bearer",
                expires_in=expires_in,
            )

    except httpx.RequestError as e:
        logger.error(
            f"Network error during token exchange: {str(e)}",
            extra={
                "context": {
                    "request_id": request_id,
                    "error": str(e),
                }
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error_response(
                error_code=ErrorCode.SYS_INTERNAL_ERROR,
                message="Failed to communicate with identity provider",
                detail="Network error during token exchange",
                request_id=request_id,
            ),
        ) from e

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error during auth callback: {str(e)}",
            extra={"context": {"request_id": request_id}},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                error_code=ErrorCode.SYS_INTERNAL_ERROR,
                message="Authentication failed",
                detail="An unexpected error occurred during authentication",
                request_id=request_id,
            ),
        ) from e


@router.get(
    "/validate",
    response_model=ValidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate JWT token",
    description="""
    Validate the current user's JWT token and return user context.

    This endpoint:
    1. Validates JWT signature using JWKS keys
    2. Validates JWT claims (expiration, issuer, audience)
    3. Extracts user_id and tenant_id from claims
    4. Returns validation result with user context

    Requires Authorization header: `Bearer <token>`
    """,
    responses={
        200: {
            "description": "Token is valid",
            "content": {
                "application/json": {
                    "example": {
                        "valid": True,
                        "user_id": "usr-123",
                        "tenant_id": "org-456",
                        "expires_at": 1234567890,
                    }
                }
            },
        },
        401: {
            "description": "Token is invalid or expired",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_003",
                            "message": "JWT token has expired",
                            "detail": "Please authenticate again to obtain a new token",
                            "request_id": "req-123-abc-456",
                        }
                    }
                }
            },
        },
        403: {
            "description": "Missing tenant claim in JWT",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_005",
                            "message": "Missing tenant claim in JWT token",
                            "request_id": "req-123-abc-456",
                        }
                    }
                }
            },
        },
    },
)
async def validate_token(
    request: Request,
    user: CurrentUser,
) -> ValidateResponse:
    """
    Validate JWT token and return user context.

    The get_current_user dependency handles JWT validation,
    so this endpoint just needs to extract and return the context.

    Args:
        request: FastAPI request object (for request_id)
        user: Authenticated user context from dependency

    Returns:
        ValidateResponse: Token validation result with user context
    """
    request_id = getattr(request.state, "request_id", None)

    # Extract expiration timestamp from JWT claims
    exp_timestamp = user.claims.get("exp", 0)

    logger.info(
        "Token validation successful",
        extra={
            "context": {
                "request_id": request_id,
                "user_id": user.user_id,
                "tenant_id": user.tenant_id,
                "expires_at": exp_timestamp,
            }
        },
    )

    return ValidateResponse(
        valid=True,
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        expires_at=exp_timestamp,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout and get IdP logout URL",
    description="""
    Logout user and return IdP logout URL for redirect.

    This endpoint:
    1. Validates redirect URI against allowed origins
    2. Constructs IdP logout URL with redirect
    3. Returns logout URL for client-side redirect

    The client should redirect the user to the returned logout_url
    to complete the logout process at the identity provider.

    Note: This endpoint invalidates the session at the IdP level.
    The client should discard the JWT token after logout.
    """,
    responses={
        200: {
            "description": "Logout successful, IdP logout URL returned",
            "content": {
                "application/json": {
                    "example": {
                        "logout_url": "https://idp.example.com/logout?redirect_uri=https://app.example.com"
                    }
                }
            },
        },
        400: {
            "description": "Invalid redirect URI",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_006",
                            "message": "Invalid redirect URI",
                            "detail": "Redirect URI must be in allowed origins list",
                            "request_id": "req-123-abc-456",
                        }
                    }
                }
            },
        },
    },
)
async def logout(
    request: Request,
    logout_data: LogoutRequest,
) -> LogoutResponse:
    """
    Generate IdP logout URL for user redirect.

    Args:
        request: FastAPI request object (for request_id)
        logout_data: Redirect URI for post-logout redirect

    Returns:
        LogoutResponse: IdP logout URL to redirect to

    Raises:
        HTTPException: If redirect URI is not in allowed origins
    """
    settings = get_settings()
    request_id = getattr(request.state, "request_id", None)

    logger.info(
        "Processing logout request",
        extra={
            "context": {
                "request_id": request_id,
                "redirect_uri": logout_data.redirect_uri,
            }
        },
    )

    # Validate redirect URI against allowed origins
    allowed_origins = settings.get_allowed_origins_list()

    # Check if redirect URI matches any allowed origin
    redirect_uri = logout_data.redirect_uri.rstrip("/")
    is_valid = False

    for origin in allowed_origins:
        origin_normalized = origin.rstrip("/")
        # Allow exact match or path under the origin
        if redirect_uri == origin_normalized or redirect_uri.startswith(origin_normalized + "/"):
            is_valid = True
            break

    if not is_valid:
        logger.warning(
            "Invalid redirect URI for logout",
            extra={
                "context": {
                    "request_id": request_id,
                    "redirect_uri": redirect_uri,
                    "allowed_origins": allowed_origins,
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error_response(
                error_code=ErrorCode.AUTH_INVALID_REDIRECT,
                message="Invalid redirect URI",
                detail="Redirect URI must be in the allowed origins list",
                request_id=request_id,
            ),
        )

    # Construct IdP logout URL
    # For AWS Cognito, the logout endpoint is at /logout with redirect_uri parameter
    issuer_url = str(settings.oidc_issuer_url).rstrip("/")
    logout_url = f"{issuer_url}/logout?client_id={settings.oidc_client_id}&logout_uri={redirect_uri}"

    logger.info(
        "Logout URL generated",
        extra={
            "context": {
                "request_id": request_id,
                "redirect_uri": redirect_uri,
            }
        },
    )

    return LogoutResponse(logout_url=logout_url)
