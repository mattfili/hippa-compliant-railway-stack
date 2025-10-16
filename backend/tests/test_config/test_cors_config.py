"""Tests for CORS configuration."""

import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the settings cache before and after each test."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def minimal_env():
    """Provide minimal required environment variables for Settings."""
    return {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "OIDC_ISSUER_URL": "https://test.example.com",
        "OIDC_CLIENT_ID": "test-client-id",
    }


def test_get_allowed_origins_from_env(minimal_env):
    """Test that allowed origins are loaded from environment variable."""
    env = {
        **minimal_env,
        "ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:5173,http://localhost:8080",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        origins = settings.get_allowed_origins_list()
        assert origins == [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
        ]


def test_get_allowed_origins_custom(minimal_env):
    """Test CORS configuration with custom origins."""
    env = {
        **minimal_env,
        "ALLOWED_ORIGINS": "https://example.com,https://app.example.com",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        origins = settings.get_allowed_origins_list()
        assert origins == ["https://example.com", "https://app.example.com"]


def test_get_allowed_origins_strips_whitespace(minimal_env):
    """Test that whitespace is properly stripped from origins."""
    env = {
        **minimal_env,
        "ALLOWED_ORIGINS": " http://localhost:3000 , http://localhost:5173 ",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        origins = settings.get_allowed_origins_list()
        assert origins == [
            "http://localhost:3000",
            "http://localhost:5173",
        ]


def test_get_allowed_origins_empty_string(minimal_env):
    """Test that empty string results in empty list."""
    env = {
        **minimal_env,
        "ALLOWED_ORIGINS": "",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        origins = settings.get_allowed_origins_list()
        assert origins == []
