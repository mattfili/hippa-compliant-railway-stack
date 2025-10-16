"""
JWKS (JSON Web Key Set) caching with automatic refresh and retry logic.

This module provides:
- In-memory JWKS key caching with configurable TTL
- Background refresh before TTL expiration to prevent cache miss latency
- Async JWKS fetching from OIDC issuer with retry logic
- Key lookup by key ID (kid) for JWT validation
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from jose import jwk

logger = logging.getLogger(__name__)


class JWKSCache:
    """
    JWKS key cache with automatic refresh and retry logic.

    Fetches JWKS keys from the OIDC issuer's .well-known/jwks.json endpoint
    and caches them in memory with a configurable TTL. Background refresh
    happens before TTL expiration to ensure hot cache.
    """

    def __init__(
        self,
        jwks_url: str,
        ttl_seconds: int = 3600,
        max_retries: int = 3,
        initial_backoff: float = 0.5,
    ):
        """
        Initialize JWKS cache.

        Args:
            jwks_url: URL of JWKS endpoint (e.g., https://issuer/.well-known/jwks.json)
            ttl_seconds: Cache TTL in seconds (default: 3600 = 1 hour)
            max_retries: Maximum fetch retry attempts (default: 3)
            initial_backoff: Initial backoff delay for retries in seconds (default: 0.5)
        """
        self.jwks_url = jwks_url
        self.ttl_seconds = ttl_seconds
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

        self._keys: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Optional[float] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def _is_cache_expired(self) -> bool:
        """Check if cache has expired based on TTL."""
        if self._cache_time is None:
            return True
        age = time.time() - self._cache_time
        return age >= self.ttl_seconds

    def _is_cache_stale(self) -> bool:
        """Check if cache is stale (80% of TTL expired) and needs refresh."""
        if self._cache_time is None:
            return True
        age = time.time() - self._cache_time
        return age >= (self.ttl_seconds * 0.8)

    async def _fetch_jwks(self) -> List[Dict[str, Any]]:
        """
        Fetch JWKS from issuer endpoint with retry logic.

        Returns:
            List[Dict[str, Any]]: List of JWK (JSON Web Key) dictionaries

        Raises:
            httpx.HTTPError: If fetching fails after all retries
        """
        backoff = self.initial_backoff
        last_error = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(self.max_retries):
                try:
                    logger.info(
                        f"Fetching JWKS from {self.jwks_url} "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )

                    response = await client.get(self.jwks_url)
                    response.raise_for_status()

                    jwks_data = response.json()
                    keys = jwks_data.get("keys", [])

                    if not keys:
                        logger.warning(f"JWKS endpoint returned no keys: {self.jwks_url}")

                    logger.info(f"Successfully fetched {len(keys)} JWKS keys")
                    return keys

                except (httpx.HTTPError, httpx.RequestError) as e:
                    last_error = e
                    logger.warning(
                        f"Failed to fetch JWKS (attempt {attempt + 1}): {str(e)}"
                    )

                    if attempt < self.max_retries - 1:
                        logger.info(f"Retrying in {backoff} seconds...")
                        await asyncio.sleep(backoff)
                        backoff *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"Failed to fetch JWKS after {self.max_retries} attempts"
                        )
                        raise last_error from e

        # This should never be reached, but satisfies type checker
        if last_error:
            raise last_error
        raise httpx.HTTPError("Failed to fetch JWKS")

    async def _refresh_cache(self) -> None:
        """Refresh cache by fetching fresh JWKS keys."""
        try:
            async with self._lock:
                logger.info("Refreshing JWKS cache")
                keys = await self._fetch_jwks()

                # Index keys by kid for fast lookup
                new_keys = {}
                for key in keys:
                    kid = key.get("kid")
                    if kid:
                        new_keys[kid] = key
                    else:
                        logger.warning("JWKS key missing 'kid' field, skipping")

                self._keys = new_keys
                self._cache_time = time.time()
                logger.info(f"JWKS cache refreshed with {len(self._keys)} keys")

        except Exception as e:
            logger.error(f"Failed to refresh JWKS cache: {str(e)}")
            # Keep existing cache if refresh fails

    async def _background_refresh(self) -> None:
        """Background task to refresh cache before TTL expiration."""
        while True:
            try:
                # Wait until cache is stale (80% of TTL)
                if self._cache_time is not None:
                    age = time.time() - self._cache_time
                    wait_time = max(0, (self.ttl_seconds * 0.8) - age)
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)

                # Refresh cache
                await self._refresh_cache()

                # Wait for full TTL before next refresh
                await asyncio.sleep(self.ttl_seconds)

            except asyncio.CancelledError:
                logger.info("JWKS background refresh task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in JWKS background refresh: {str(e)}")
                # Wait before retrying on error
                await asyncio.sleep(60)

    def start_background_refresh(self) -> None:
        """Start background refresh task."""
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._background_refresh())
            logger.info("Started JWKS background refresh task")

    def stop_background_refresh(self) -> None:
        """Stop background refresh task."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            logger.info("Stopped JWKS background refresh task")

    async def get_key(self, kid: str) -> Optional[Dict[str, Any]]:
        """
        Get JWKS key by key ID (kid).

        If cache is expired or key is not found, fetches fresh JWKS.

        Args:
            kid: Key ID from JWT header

        Returns:
            Optional[Dict[str, Any]]: JWK dictionary or None if not found

        Raises:
            httpx.HTTPError: If fetching JWKS fails
        """
        # Refresh cache if expired
        if self._is_cache_expired():
            logger.info("JWKS cache expired, refreshing")
            await self._refresh_cache()

        # Try to get key from cache
        key = self._keys.get(kid)

        if key is None:
            # Key not found - might be a new key, refresh cache
            logger.warning(f"Key ID '{kid}' not found in cache, refreshing JWKS")
            await self._refresh_cache()
            key = self._keys.get(kid)

            if key is None:
                logger.error(f"Key ID '{kid}' not found in JWKS after refresh")
                return None

        return key

    async def get_signing_key(self, kid: str) -> Any:
        """
        Get RSA signing key for JWT verification.

        Args:
            kid: Key ID from JWT header

        Returns:
            RSA public key for signature verification

        Raises:
            ValueError: If key is not found or is invalid
            httpx.HTTPError: If fetching JWKS fails
        """
        key_dict = await self.get_key(kid)

        if key_dict is None:
            raise ValueError(f"Signing key with kid '{kid}' not found in JWKS")

        # Convert JWK to RSA key using python-jose
        try:
            key = jwk.construct(key_dict)
            return key
        except Exception as e:
            logger.error(f"Failed to construct signing key from JWK: {str(e)}")
            raise ValueError(f"Invalid JWK for kid '{kid}'") from e

    def clear_cache(self) -> None:
        """Clear cached JWKS keys."""
        self._keys.clear()
        self._cache_time = None
        logger.info("JWKS cache cleared")
