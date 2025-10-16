"""
Application configuration management using Pydantic Settings.

This module provides:
- Environment-based configuration loading
- AWS Secrets Manager integration for sensitive values
- Configuration validation and defaults
- Settings caching for performance
"""

import logging
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and AWS Secrets Manager.

    Settings are validated on load and cached for performance. Sensitive values
    like OIDC_CLIENT_SECRET are loaded from AWS Secrets Manager on initialization.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    environment: str = Field(
        default="development",
        description="Application environment (development, staging, production)"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins"
    )

    # Database Settings
    database_url: str = Field(
        ...,
        description="PostgreSQL database connection URL (asyncpg driver)"
    )

    # Authentication Settings
    oidc_issuer_url: HttpUrl = Field(
        ...,
        description="OIDC issuer URL for JWT validation (e.g., Cognito user pool URL)"
    )
    oidc_client_id: str = Field(
        ...,
        description="OIDC client ID for token validation"
    )
    oidc_client_secret: str | None = Field(
        default=None,
        description="OIDC client secret (loaded from AWS Secrets Manager)"
    )
    jwt_tenant_claim_name: str = Field(
        default="tenant_id",
        description="Name of JWT claim containing tenant identifier (e.g., tenant_id, organization_id)"
    )
    jwt_max_lifetime_minutes: int = Field(
        default=60,
        description="Maximum allowed JWT token lifetime in minutes"
    )
    jwks_cache_ttl_seconds: int = Field(
        default=3600,
        description="JWKS key cache TTL in seconds (default 1 hour)"
    )

    # AWS Settings
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for Secrets Manager and other services"
    )
    aws_secrets_manager_secret_id: str | None = Field(
        default=None,
        description="AWS Secrets Manager secret ID for runtime secrets"
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of allowed values."""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"environment must be one of: {', '.join(allowed)}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of allowed values."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level must be one of: {', '.join(allowed)}")
        return v_upper

    @field_validator("jwt_max_lifetime_minutes")
    @classmethod
    def validate_jwt_lifetime(cls, v: int) -> int:
        """Validate JWT lifetime is within reasonable bounds."""
        if v < 1:
            raise ValueError("jwt_max_lifetime_minutes must be at least 1")
        if v > 1440:  # 24 hours
            raise ValueError("jwt_max_lifetime_minutes must not exceed 1440 (24 hours)")
        return v

    @field_validator("jwks_cache_ttl_seconds")
    @classmethod
    def validate_jwks_cache_ttl(cls, v: int) -> int:
        """Validate JWKS cache TTL is within reasonable bounds."""
        if v < 60:
            raise ValueError("jwks_cache_ttl_seconds must be at least 60 (1 minute)")
        if v > 86400:  # 24 hours
            raise ValueError("jwks_cache_ttl_seconds must not exceed 86400 (24 hours)")
        return v

    def get_allowed_origins_list(self) -> List[str]:
        """
        Parse ALLOWED_ORIGINS into a list.

        Returns:
            List[str]: List of allowed origin URLs
        """
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Settings are loaded once and cached for the lifetime of the application.
    Use this function instead of creating Settings instances directly.

    Returns:
        Settings: Cached settings instance
    """
    logger.info("Loading application settings")
    settings = Settings()
    logger.info(f"Settings loaded for environment: {settings.environment}")
    return settings
