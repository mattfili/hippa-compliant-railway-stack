"""
AWS Secrets Manager client for secure runtime secret retrieval.

This module provides:
- Async secret fetching from AWS Secrets Manager
- Retry logic with exponential backoff for transient failures
- In-memory secret caching (no disk writes)
- Graceful fallback for local development without AWS credentials
"""

import asyncio
import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class SecretsManagerClient:
    """
    Async client for AWS Secrets Manager with retry logic.

    Handles fetching runtime secrets with exponential backoff retry
    for transient failures. Caches secrets in memory for performance.
    """

    def __init__(
        self,
        region: str,
        max_retries: int = 3,
        initial_backoff: float = 0.5,
    ):
        """
        Initialize Secrets Manager client.

        Args:
            region: AWS region for Secrets Manager
            max_retries: Maximum number of retry attempts (default: 3)
            initial_backoff: Initial backoff delay in seconds (default: 0.5)
        """
        self.region = region
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._client = None

    def _get_client(self):
        """Get or create boto3 Secrets Manager client."""
        if self._client is None:
            self._client = boto3.client(
                "secretsmanager",
                region_name=self.region,
            )
        return self._client

    async def get_secret(
        self,
        secret_id: str,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieve secret from AWS Secrets Manager with retry logic.

        Args:
            secret_id: AWS Secrets Manager secret ID or ARN
            use_cache: Whether to use cached value if available (default: True)

        Returns:
            Dict[str, Any]: Parsed secret dictionary

        Raises:
            NoCredentialsError: If AWS credentials are not configured
            ClientError: If secret retrieval fails after all retries
            ValueError: If secret JSON is invalid
        """
        # Check cache first
        if use_cache and secret_id in self._cache:
            logger.debug(f"Using cached secret: {secret_id}")
            return self._cache[secret_id]

        backoff = self.initial_backoff
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Fetching secret '{secret_id}' from AWS Secrets Manager "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )

                # Run boto3 call in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self._get_client().get_secret_value(SecretId=secret_id)
                )

                # Parse secret string as JSON
                secret_string = response.get("SecretString")
                if not secret_string:
                    raise ValueError(f"Secret '{secret_id}' has no SecretString value")

                secret_dict = json.loads(secret_string)

                # Cache the result
                self._cache[secret_id] = secret_dict
                logger.info(f"Successfully fetched and cached secret: {secret_id}")

                return secret_dict

            except NoCredentialsError as e:
                # Don't retry credential errors
                logger.warning(
                    f"AWS credentials not configured. Skipping secret fetch: {secret_id}"
                )
                raise e

            except (BotoCoreError, ClientError) as e:
                last_error = e
                error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "Unknown")
                logger.warning(
                    f"Failed to fetch secret '{secret_id}' (attempt {attempt + 1}): "
                    f"{error_code} - {str(e)}"
                )

                # Don't retry client errors like ResourceNotFoundException
                if error_code in ["ResourceNotFoundException", "AccessDeniedException"]:
                    logger.error(f"Non-retryable error fetching secret: {error_code}")
                    raise e

                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {backoff} seconds...")
                    await asyncio.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                else:
                    logger.error(
                        f"Failed to fetch secret '{secret_id}' after {self.max_retries} attempts"
                    )
                    raise last_error from e

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in secret '{secret_id}': {str(e)}")
                raise ValueError(f"Secret '{secret_id}' contains invalid JSON") from e

        # This should never be reached, but satisfies type checker
        if last_error:
            raise last_error
        raise ClientError(
            {"Error": {"Code": "UnknownError", "Message": "Failed to fetch secret"}},
            "get_secret_value"
        )

    async def get_secret_value(
        self,
        secret_id: str,
        key: str,
        use_cache: bool = True,
    ) -> str:
        """
        Retrieve a specific value from a secret.

        Args:
            secret_id: AWS Secrets Manager secret ID or ARN
            key: Key within the secret dictionary
            use_cache: Whether to use cached value if available (default: True)

        Returns:
            str: Secret value for the specified key

        Raises:
            KeyError: If key is not found in secret
            NoCredentialsError: If AWS credentials are not configured
            ClientError: If secret retrieval fails
        """
        secret = await self.get_secret(secret_id, use_cache=use_cache)

        if key not in secret:
            raise KeyError(f"Key '{key}' not found in secret '{secret_id}'")

        return secret[key]

    def clear_cache(self, secret_id: str | None = None) -> None:
        """
        Clear cached secrets.

        Args:
            secret_id: Optional secret ID to clear. If None, clears entire cache.
        """
        if secret_id is None:
            self._cache.clear()
            logger.info("Cleared all cached secrets")
        elif secret_id in self._cache:
            del self._cache[secret_id]
            logger.info(f"Cleared cached secret: {secret_id}")


async def load_secrets_into_settings(settings) -> None:
    """
    Load runtime secrets from AWS Secrets Manager into settings.

    This function is called during application startup to populate
    sensitive configuration values from AWS Secrets Manager.

    Args:
        settings: Application settings instance to populate

    Note:
        If AWS credentials are not available (local development),
        this function logs a warning but does not raise an error.
    """
    if not settings.aws_secrets_manager_secret_id:
        logger.info("No AWS Secrets Manager secret ID configured, skipping secret loading")
        return

    try:
        client = SecretsManagerClient(region=settings.aws_region)

        # Fetch OIDC client secret if not already set
        if not settings.oidc_client_secret:
            try:
                settings.oidc_client_secret = await client.get_secret_value(
                    settings.aws_secrets_manager_secret_id,
                    "OIDC_CLIENT_SECRET",
                )
                logger.info("Successfully loaded OIDC_CLIENT_SECRET from AWS Secrets Manager")
            except KeyError:
                logger.warning(
                    "OIDC_CLIENT_SECRET not found in AWS Secrets Manager secret. "
                    "Ensure the secret contains this key."
                )

    except NoCredentialsError:
        logger.warning(
            "AWS credentials not configured. Skipping AWS Secrets Manager integration. "
            "This is normal for local development."
        )
    except Exception as e:
        logger.error(f"Failed to load secrets from AWS Secrets Manager: {str(e)}")
        # Don't crash application - allow startup with partial configuration
        logger.warning("Application starting with incomplete secret configuration")
