"""
JWT token validation with signature verification and claims validation.

This module provides:
- JWT signature verification using JWKS public keys
- Standard JWT claims validation (exp, iat, iss, aud)
- Token lifetime enforcement (max 60 minutes by default)
- Decoded claims extraction for downstream use
"""

import logging
import time
from typing import Any, Dict

from jose import jwt, JWTError

from app.auth.jwks_cache import JWKSCache

logger = logging.getLogger(__name__)


class JWTValidationError(Exception):
    """Base exception for JWT validation errors."""
    pass


class TokenExpiredError(JWTValidationError):
    """Raised when JWT token has expired."""
    pass


class TokenSignatureError(JWTValidationError):
    """Raised when JWT signature verification fails."""
    pass


class TokenInvalidClaimError(JWTValidationError):
    """Raised when JWT claims are invalid."""
    pass


class JWTValidator:
    """
    JWT token validator with signature and claims verification.

    Validates JWT tokens from OIDC/SAML identity providers:
    - Fetches public keys from JWKS endpoint
    - Verifies token signature using RSA public key
    - Validates standard claims (exp, iat, iss, aud)
    - Enforces maximum token lifetime
    """

    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        jwks_cache: JWKSCache,
        max_lifetime_minutes: int = 60,
        leeway_seconds: int = 60,
    ):
        """
        Initialize JWT validator.

        Args:
            issuer_url: OIDC issuer URL for token validation
            client_id: Expected audience (client ID) in JWT
            jwks_cache: JWKS cache instance for key lookup
            max_lifetime_minutes: Maximum allowed token lifetime (default: 60)
            leeway_seconds: Clock skew tolerance in seconds (default: 60)
        """
        self.issuer_url = str(issuer_url).rstrip("/")
        self.client_id = client_id
        self.jwks_cache = jwks_cache
        self.max_lifetime_minutes = max_lifetime_minutes
        self.leeway_seconds = leeway_seconds

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return decoded claims.

        Performs complete token validation:
        1. Parse JWT header to extract key ID (kid)
        2. Fetch signing key from JWKS cache
        3. Verify token signature
        4. Validate standard claims (exp, iat, iss, aud)
        5. Enforce maximum token lifetime

        Args:
            token: JWT token string

        Returns:
            Dict[str, Any]: Decoded JWT claims

        Raises:
            JWTValidationError: If validation fails for any reason
            TokenExpiredError: If token has expired
            TokenSignatureError: If signature verification fails
            TokenInvalidClaimError: If claims are invalid
        """
        try:
            # Parse JWT header without verification to get kid
            unverified_headers = jwt.get_unverified_headers(token)
            kid = unverified_headers.get("kid")

            if not kid:
                logger.warning("JWT token missing 'kid' in header")
                raise TokenInvalidClaimError("JWT token missing 'kid' in header")

            # Get signing key from JWKS cache
            try:
                signing_key = await self.jwks_cache.get_signing_key(kid)
            except ValueError as e:
                logger.warning(f"Failed to get signing key: {str(e)}")
                raise TokenSignatureError(f"Invalid signing key: {str(e)}") from e
            except Exception as e:
                logger.error(f"Error fetching signing key: {str(e)}")
                raise TokenSignatureError(f"Failed to fetch signing key: {str(e)}") from e

            # Verify signature and decode claims
            try:
                claims = jwt.decode(
                    token,
                    signing_key,
                    algorithms=["RS256"],
                    audience=self.client_id,
                    issuer=self.issuer_url,
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_iat": True,
                        "verify_aud": True,
                        "verify_iss": True,
                        "leeway": self.leeway_seconds,
                    },
                )
            except jwt.ExpiredSignatureError as e:
                logger.warning("JWT token has expired")
                raise TokenExpiredError("JWT token has expired") from e
            except jwt.JWTClaimsError as e:
                logger.warning(f"JWT claims validation failed: {str(e)}")
                raise TokenInvalidClaimError(f"Invalid JWT claims: {str(e)}") from e
            except JWTError as e:
                logger.warning(f"JWT signature verification failed: {str(e)}")
                raise TokenSignatureError(f"JWT signature verification failed: {str(e)}") from e

            # Validate token lifetime does not exceed maximum
            self._validate_token_lifetime(claims)

            logger.info(
                f"Successfully validated JWT token for user: {claims.get('sub', 'unknown')}"
            )
            return claims

        except JWTValidationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error during JWT validation: {str(e)}")
            raise JWTValidationError(f"JWT validation failed: {str(e)}") from e

    def _validate_token_lifetime(self, claims: Dict[str, Any]) -> None:
        """
        Validate token lifetime does not exceed maximum allowed.

        Args:
            claims: Decoded JWT claims

        Raises:
            TokenInvalidClaimError: If token lifetime exceeds maximum
        """
        iat = claims.get("iat")
        exp = claims.get("exp")

        if not iat or not exp:
            logger.warning("JWT token missing 'iat' or 'exp' claim")
            raise TokenInvalidClaimError("JWT token missing 'iat' or 'exp' claim")

        # Calculate token lifetime in minutes
        lifetime_seconds = exp - iat
        lifetime_minutes = lifetime_seconds / 60

        if lifetime_minutes > self.max_lifetime_minutes:
            logger.warning(
                f"JWT token lifetime ({lifetime_minutes:.1f} minutes) "
                f"exceeds maximum ({self.max_lifetime_minutes} minutes)"
            )
            raise TokenInvalidClaimError(
                f"Token lifetime exceeds maximum of {self.max_lifetime_minutes} minutes"
            )

        logger.debug(f"Token lifetime: {lifetime_minutes:.1f} minutes (within limit)")

    async def validate_token_claims(
        self,
        token: str,
        required_claims: list[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Validate token and check for required custom claims.

        Args:
            token: JWT token string
            required_claims: List of required claim names (optional)

        Returns:
            Dict[str, Any]: Decoded JWT claims

        Raises:
            JWTValidationError: If validation fails
            TokenInvalidClaimError: If required claims are missing
        """
        claims = await self.validate_token(token)

        if required_claims:
            missing_claims = [
                claim for claim in required_claims
                if claim not in claims
            ]

            if missing_claims:
                logger.warning(f"JWT token missing required claims: {missing_claims}")
                raise TokenInvalidClaimError(
                    f"JWT token missing required claims: {', '.join(missing_claims)}"
                )

        return claims

    def extract_user_id(self, claims: Dict[str, Any]) -> str:
        """
        Extract user ID from JWT claims.

        Args:
            claims: Decoded JWT claims

        Returns:
            str: User ID from 'sub' claim

        Raises:
            TokenInvalidClaimError: If 'sub' claim is missing
        """
        user_id = claims.get("sub")

        if not user_id:
            logger.warning("JWT token missing 'sub' (user ID) claim")
            raise TokenInvalidClaimError("JWT token missing 'sub' (user ID) claim")

        return user_id
