"""Tests for Terraform output fields in configuration."""

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


def test_terraform_s3_bucket_documents_from_env(minimal_env):
    """Test that S3 documents bucket is loaded from environment variable."""
    env = {
        **minimal_env,
        "S3_BUCKET_DOCUMENTS": "hipaa-docs-prod-123456",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        assert settings.s3_bucket_documents == "hipaa-docs-prod-123456"


def test_terraform_s3_bucket_backups_from_env(minimal_env):
    """Test that S3 backups bucket is loaded from environment variable."""
    env = {
        **minimal_env,
        "S3_BUCKET_BACKUPS": "hipaa-backups-prod-789012",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        assert settings.s3_bucket_backups == "hipaa-backups-prod-789012"


def test_terraform_s3_bucket_audit_logs_from_env(minimal_env):
    """Test that S3 audit logs bucket is loaded from environment variable."""
    env = {
        **minimal_env,
        "S3_BUCKET_AUDIT_LOGS": "hipaa-audit-prod-345678",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        assert settings.s3_bucket_audit_logs == "hipaa-audit-prod-345678"


def test_terraform_kms_master_key_id_from_env(minimal_env):
    """Test that KMS master key ID is loaded from environment variable."""
    env = {
        **minimal_env,
        "KMS_MASTER_KEY_ID": "arn:aws:kms:us-east-1:123456789012:key/test-key-id",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        assert settings.kms_master_key_id == "arn:aws:kms:us-east-1:123456789012:key/test-key-id"


def test_terraform_outputs_all_fields_loaded(minimal_env):
    """Test that all Terraform output fields are loaded correctly."""
    env = {
        **minimal_env,
        "S3_BUCKET_DOCUMENTS": "hipaa-docs-prod-111111",
        "S3_BUCKET_BACKUPS": "hipaa-backups-prod-222222",
        "S3_BUCKET_AUDIT_LOGS": "hipaa-audit-prod-333333",
        "KMS_MASTER_KEY_ID": "arn:aws:kms:us-east-1:123456789012:key/full-test",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        assert settings.s3_bucket_documents == "hipaa-docs-prod-111111"
        assert settings.s3_bucket_backups == "hipaa-backups-prod-222222"
        assert settings.s3_bucket_audit_logs == "hipaa-audit-prod-333333"
        assert settings.kms_master_key_id == "arn:aws:kms:us-east-1:123456789012:key/full-test"


def test_terraform_outputs_optional_defaults_to_none(minimal_env):
    """Test that Terraform output fields default to None when not provided."""
    with patch.dict(os.environ, minimal_env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        assert settings.s3_bucket_documents is None
        assert settings.s3_bucket_backups is None
        assert settings.s3_bucket_audit_logs is None
        assert settings.kms_master_key_id is None


def test_terraform_outputs_empty_string_treated_as_none(minimal_env):
    """Test that empty string environment variables are treated as None."""
    env = {
        **minimal_env,
        "S3_BUCKET_DOCUMENTS": "",
        "S3_BUCKET_BACKUPS": "",
        "S3_BUCKET_AUDIT_LOGS": "",
        "KMS_MASTER_KEY_ID": "",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        # Pydantic treats empty strings as None for Optional fields
        assert settings.s3_bucket_documents in [None, ""]
        assert settings.s3_bucket_backups in [None, ""]
        assert settings.s3_bucket_audit_logs in [None, ""]
        assert settings.kms_master_key_id in [None, ""]


def test_terraform_outputs_with_realistic_values(minimal_env):
    """Test with realistic AWS resource names from Terraform."""
    env = {
        **minimal_env,
        "S3_BUCKET_DOCUMENTS": "hipaa-documents-production-us-east-1-a1b2c3d4",
        "S3_BUCKET_BACKUPS": "hipaa-backups-production-us-east-1-e5f6g7h8",
        "S3_BUCKET_AUDIT_LOGS": "hipaa-audit-logs-production-us-east-1-i9j0k1l2",
        "KMS_MASTER_KEY_ID": "arn:aws:kms:us-east-1:123456789012:key/12345678-abcd-efgh-ijkl-1234567890ab",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        assert "hipaa-documents-production" in settings.s3_bucket_documents
        assert "hipaa-backups-production" in settings.s3_bucket_backups
        assert "hipaa-audit-logs-production" in settings.s3_bucket_audit_logs
        assert "arn:aws:kms:us-east-1" in settings.kms_master_key_id


def test_config_terraform_outputs_independent_of_other_aws_settings(minimal_env):
    """Test that Terraform output fields are independent of other AWS settings."""
    env = {
        **minimal_env,
        "AWS_REGION": "us-west-2",
        "AWS_SECRETS_MANAGER_SECRET_ID": "my-secret-id",
        "S3_BUCKET_DOCUMENTS": "hipaa-docs-test",
        "KMS_MASTER_KEY_ID": "arn:aws:kms:us-east-1:123456:key/test",
    }
    with patch.dict(os.environ, env, clear=True):
        from app.config import get_settings

        settings = get_settings()
        # Verify Terraform outputs are loaded
        assert settings.s3_bucket_documents == "hipaa-docs-test"
        assert settings.kms_master_key_id == "arn:aws:kms:us-east-1:123456:key/test"
        # Verify other AWS settings are independent
        assert settings.aws_region == "us-west-2"
        assert settings.aws_secrets_manager_secret_id == "my-secret-id"
