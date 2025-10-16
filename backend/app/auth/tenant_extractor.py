"""
Tenant ID extraction from JWT claims.

This module provides:
- Tenant ID extraction from configurable JWT claim names
- Tenant ID format validation
- Priority-based claim name resolution
- Error handling for missing tenant claims
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class TenantExtractionError(Exception):
    """Base exception for tenant extraction errors."""
    pass


class MissingTenantClaimError(TenantExtractionError):
    """Raised when tenant claim is not found in JWT."""
    pass


class InvalidTenantFormatError(TenantExtractionError):
    """Raised when tenant ID format is invalid."""
    pass


class TenantExtractor:
    """
    Extract and validate tenant ID from JWT claims.

    Supports configurable claim names with priority order for
    multi-IdP compatibility (tenant_id, organization_id, org_id, etc.).
    """

    # Default claim names to check in priority order
    DEFAULT_CLAIM_NAMES = [
        "tenant_id",
        "organization_id",
        "org_id",
        "custom:tenant_id",  # AWS Cognito custom attribute format
    ]

    # Regex pattern for valid tenant ID format (alphanumeric, hyphens, underscores)
    # Examples: org-123, tenant_abc, org123, ORG-UUID-1234
    TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    def __init__(
        self,
        claim_names: List[str] | None = None,
        validate_format: bool = True,
        min_length: int = 3,
        max_length: int = 128,
    ):
        """
        Initialize tenant extractor.

        Args:
            claim_names: Ordered list of claim names to check (default: DEFAULT_CLAIM_NAMES)
            validate_format: Whether to validate tenant ID format (default: True)
            min_length: Minimum tenant ID length (default: 3)
            max_length: Maximum tenant ID length (default: 128)
        """
        self.claim_names = claim_names or self.DEFAULT_CLAIM_NAMES
        self.validate_format = validate_format
        self.min_length = min_length
        self.max_length = max_length

    def extract_tenant_id(self, claims: Dict[str, Any]) -> str:
        """
        Extract tenant ID from JWT claims.

        Checks claim names in priority order and returns the first valid value found.

        Args:
            claims: Decoded JWT claims dictionary

        Returns:
            str: Validated tenant ID

        Raises:
            MissingTenantClaimError: If no tenant claim is found
            InvalidTenantFormatError: If tenant ID format is invalid
        """
        # Try each claim name in priority order
        for claim_name in self.claim_names:
            tenant_id = claims.get(claim_name)

            if tenant_id:
                logger.debug(f"Found tenant ID in claim '{claim_name}': {tenant_id}")

                # Validate format if enabled
                if self.validate_format:
                    self._validate_tenant_id(tenant_id, claim_name)

                return str(tenant_id)

        # No tenant claim found
        logger.warning(
            f"Tenant ID not found in JWT claims. Checked claims: {', '.join(self.claim_names)}"
        )
        raise MissingTenantClaimError(
            f"JWT token missing tenant claim. Expected one of: {', '.join(self.claim_names)}"
        )

    def _validate_tenant_id(self, tenant_id: str, claim_name: str) -> None:
        """
        Validate tenant ID format.

        Args:
            tenant_id: Tenant ID to validate
            claim_name: Name of claim for error messages

        Raises:
            InvalidTenantFormatError: If tenant ID format is invalid
        """
        # Check type
        if not isinstance(tenant_id, str):
            logger.warning(
                f"Tenant ID from claim '{claim_name}' is not a string: {type(tenant_id)}"
            )
            raise InvalidTenantFormatError(
                f"Tenant ID must be a string (got {type(tenant_id).__name__})"
            )

        # Check length
        if len(tenant_id) < self.min_length:
            logger.warning(
                f"Tenant ID '{tenant_id}' is too short (minimum: {self.min_length})"
            )
            raise InvalidTenantFormatError(
                f"Tenant ID must be at least {self.min_length} characters"
            )

        if len(tenant_id) > self.max_length:
            logger.warning(
                f"Tenant ID '{tenant_id}' is too long (maximum: {self.max_length})"
            )
            raise InvalidTenantFormatError(
                f"Tenant ID must not exceed {self.max_length} characters"
            )

        # Check format (alphanumeric, hyphens, underscores only)
        if not self.TENANT_ID_PATTERN.match(tenant_id):
            logger.warning(
                f"Tenant ID '{tenant_id}' contains invalid characters"
            )
            raise InvalidTenantFormatError(
                "Tenant ID must contain only alphanumeric characters, hyphens, and underscores"
            )

        logger.debug(f"Tenant ID '{tenant_id}' passed validation")

    def extract_with_user_id(
        self,
        claims: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Extract both tenant ID and user ID from JWT claims.

        Args:
            claims: Decoded JWT claims dictionary

        Returns:
            tuple[str, str]: (tenant_id, user_id)

        Raises:
            MissingTenantClaimError: If tenant claim is missing
            InvalidTenantFormatError: If tenant ID format is invalid
            ValueError: If user ID (sub claim) is missing
        """
        tenant_id = self.extract_tenant_id(claims)

        user_id = claims.get("sub")
        if not user_id:
            logger.warning("JWT token missing 'sub' (user ID) claim")
            raise ValueError("JWT token missing 'sub' (user ID) claim")

        return tenant_id, str(user_id)


def create_tenant_extractor(tenant_claim_name: str) -> TenantExtractor:
    """
    Create tenant extractor with single claim name.

    Convenience function for creating an extractor that only checks one claim name.

    Args:
        tenant_claim_name: Name of JWT claim containing tenant ID

    Returns:
        TenantExtractor: Configured extractor instance
    """
    return TenantExtractor(claim_names=[tenant_claim_name])
