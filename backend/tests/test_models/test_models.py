"""
Tests for SQLAlchemy domain models.

Tests cover:
- Tenant model creation and soft delete
- User model with tenant relationship and partial unique index
- Document model with vector similarity search
- AuditLog model append-only enforcement
- Model relationships (Tenant.users, User.documents, etc.)
- Soft delete allows email reuse (partial unique index)
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import AuditLog, Document, Tenant, User


@pytest.mark.asyncio
async def test_tenant_model_creation_and_soft_delete(db_session):
    """Test Tenant model creation and soft delete functionality."""
    # Create tenant
    tenant = Tenant(
        name="Test Organization",
        status="active",
        kms_key_arn="arn:aws:kms:us-east-1:123456789012:key/test-key-id",
    )
    db_session.add(tenant)
    await db_session.flush()

    # Verify tenant created with correct attributes
    assert tenant.id is not None
    assert tenant.name == "Test Organization"
    assert tenant.status == "active"
    assert tenant.kms_key_arn == "arn:aws:kms:us-east-1:123456789012:key/test-key-id"
    assert tenant.created_at is not None
    assert tenant.updated_at is not None
    assert tenant.deleted_at is None
    assert tenant.is_active is True
    assert tenant.is_deleted is False

    # Soft delete tenant
    tenant.soft_delete()
    await db_session.flush()

    # Verify tenant is soft deleted
    assert tenant.deleted_at is not None
    assert tenant.is_active is False
    assert tenant.is_deleted is True
    assert isinstance(tenant.deleted_at, datetime)

    # Restore tenant
    tenant.restore()
    await db_session.flush()

    # Verify tenant is restored
    assert tenant.deleted_at is None
    assert tenant.is_active is True
    assert tenant.is_deleted is False


@pytest.mark.asyncio
async def test_user_model_with_tenant_relationship(db_session):
    """Test User model with tenant relationship and foreign key constraint."""
    # Create tenant first
    tenant = Tenant(name="Test Org", status="active")
    db_session.add(tenant)
    await db_session.flush()

    # Create user
    user = User(
        tenant_id=tenant.id,
        email="user@example.com",
        external_idp_id="cognito-sub-123",
        full_name="Test User",
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()

    # Verify user created with correct attributes
    assert user.id is not None
    assert user.tenant_id == tenant.id
    assert user.email == "user@example.com"
    assert user.external_idp_id == "cognito-sub-123"
    assert user.full_name == "Test User"
    assert user.role == "admin"
    assert user.last_login_at is None
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.deleted_at is None

    # Verify relationship works
    await db_session.refresh(tenant, ["users"])
    assert len(tenant.users) == 1
    assert tenant.users[0].id == user.id

    # Verify user.tenant relationship
    await db_session.refresh(user, ["tenant"])
    assert user.tenant.id == tenant.id
    assert user.tenant.name == "Test Org"


@pytest.mark.asyncio
async def test_user_email_reuse_after_soft_delete(db_session):
    """Test that partial unique index allows email reuse after soft deletion."""
    # Create tenant
    tenant = Tenant(name="Test Org", status="active")
    db_session.add(tenant)
    await db_session.flush()

    # Create first user
    user1 = User(
        tenant_id=tenant.id,
        email="reuse@example.com",
        full_name="User 1",
    )
    db_session.add(user1)
    await db_session.flush()

    # Try to create duplicate email (should fail)
    user2 = User(
        tenant_id=tenant.id,
        email="reuse@example.com",
        full_name="User 2",
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()

    # Soft delete first user
    user1.soft_delete()
    await db_session.commit()

    # Now create new user with same email (should succeed)
    user3 = User(
        tenant_id=tenant.id,
        email="reuse@example.com",
        full_name="User 3",
    )
    db_session.add(user3)
    await db_session.commit()

    # Verify both users exist
    result = await db_session.execute(select(User).where(User.email == "reuse@example.com"))
    users = result.scalars().all()
    assert len(users) == 2
    assert user1.is_deleted is True
    assert user3.is_active is True


@pytest.mark.asyncio
async def test_document_model_with_vector_search(db_session):
    """Test Document model with vector embedding and similarity search."""
    # Create tenant and user
    tenant = Tenant(name="Test Org", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id,
        email="user@example.com",
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    # Create document with embedding
    embedding = [0.1] * 1024  # 1024-dimensional vector
    document = Document(
        tenant_id=tenant.id,
        user_id=user.id,
        s3_key="documents/test/doc1.pdf",
        s3_bucket="test-bucket",
        filename="test.pdf",
        content_type="application/pdf",
        size_bytes=1024000,
        status="completed",
        doc_metadata={"source": "upload", "version": 1},
        embedding_vector=embedding,
    )
    db_session.add(document)
    await db_session.flush()

    # Verify document created with correct attributes
    assert document.id is not None
    assert document.tenant_id == tenant.id
    assert document.user_id == user.id
    assert document.s3_key == "documents/test/doc1.pdf"
    assert document.s3_bucket == "test-bucket"
    assert document.filename == "test.pdf"
    assert document.content_type == "application/pdf"
    assert document.size_bytes == 1024000
    assert document.status == "completed"
    assert document.doc_metadata == {"source": "upload", "version": 1}
    assert document.embedding_vector is not None
    assert len(document.embedding_vector) == 1024

    # Test similarity_search classmethod
    query_embedding = [0.1] * 1024  # Similar vector
    stmt = Document.similarity_search(
        embedding=query_embedding,
        tenant_id=tenant.id,
        limit=10,
        threshold=0.7,
    )

    # Verify query is properly formed (this will be executed in integration tests)
    assert stmt is not None


@pytest.mark.asyncio
async def test_audit_log_append_only_enforcement(db_session):
    """Test AuditLog model append-only enforcement."""
    # Create tenant and user
    tenant = Tenant(name="Test Org", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id,
        email="user@example.com",
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    # Create audit log using create() classmethod
    resource_id = str(uuid.uuid4())
    audit_log = await AuditLog.create(
        db=db_session,
        tenant_id=tenant.id,
        user_id=user.id,
        action="document.uploaded",
        resource_type="document",
        resource_id=resource_id,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        audit_metadata={"filename": "test.pdf", "size": 1024},
    )

    # Verify audit log created with correct attributes
    assert audit_log.id is not None
    assert audit_log.tenant_id == tenant.id
    assert audit_log.user_id == user.id
    assert audit_log.action == "document.uploaded"
    assert audit_log.resource_type == "document"
    assert audit_log.resource_id == resource_id
    assert audit_log.ip_address == "192.168.1.1"
    assert audit_log.user_agent == "Mozilla/5.0"
    assert audit_log.audit_metadata == {"filename": "test.pdf", "size": 1024}
    assert audit_log.created_at is not None
    # Verify updated_at is NOT present on AuditLog
    assert not hasattr(audit_log, "updated_at") or audit_log.updated_at is None
    assert not hasattr(audit_log, "deleted_at")

    await db_session.commit()

    # Try to update audit log (should fail at database level via trigger)
    audit_log.action = "document.deleted"
    with pytest.raises(Exception):  # Database trigger will prevent UPDATE
        await db_session.commit()


@pytest.mark.asyncio
async def test_model_relationships(db_session):
    """Test relationships between models."""
    # Create tenant
    tenant = Tenant(name="Test Org", status="active")
    db_session.add(tenant)
    await db_session.flush()

    # Create users
    user1 = User(tenant_id=tenant.id, email="user1@example.com", full_name="User 1")
    user2 = User(tenant_id=tenant.id, email="user2@example.com", full_name="User 2")
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Create documents
    doc1 = Document(
        tenant_id=tenant.id,
        user_id=user1.id,
        s3_key="doc1.pdf",
        s3_bucket="bucket",
        filename="doc1.pdf",
        status="completed",
    )
    doc2 = Document(
        tenant_id=tenant.id,
        user_id=user1.id,
        s3_key="doc2.pdf",
        s3_bucket="bucket",
        filename="doc2.pdf",
        status="completed",
    )
    doc3 = Document(
        tenant_id=tenant.id,
        user_id=user2.id,
        s3_key="doc3.pdf",
        s3_bucket="bucket",
        filename="doc3.pdf",
        status="completed",
    )
    db_session.add_all([doc1, doc2, doc3])
    await db_session.flush()

    # Create audit logs
    audit1 = await AuditLog.create(
        db=db_session,
        tenant_id=tenant.id,
        user_id=user1.id,
        action="document.uploaded",
        resource_type="document",
        resource_id=doc1.id,
        audit_metadata={},
    )
    audit2 = await AuditLog.create(
        db=db_session,
        tenant_id=tenant.id,
        user_id=None,  # System action
        action="system.maintenance",
        resource_type="system",
        resource_id=tenant.id,
        audit_metadata={},
    )

    await db_session.commit()

    # Test Tenant.users relationship
    await db_session.refresh(tenant, ["users"])
    assert len(tenant.users) == 2
    user_emails = {u.email for u in tenant.users}
    assert user_emails == {"user1@example.com", "user2@example.com"}

    # Test Tenant.documents relationship
    await db_session.refresh(tenant, ["documents"])
    assert len(tenant.documents) == 3

    # Test Tenant.audit_logs relationship
    await db_session.refresh(tenant, ["audit_logs"])
    assert len(tenant.audit_logs) == 2

    # Test User.documents relationship
    await db_session.refresh(user1, ["documents"])
    assert len(user1.documents) == 2

    await db_session.refresh(user2, ["documents"])
    assert len(user2.documents) == 1

    # Test User.audit_logs relationship
    await db_session.refresh(user1, ["audit_logs"])
    assert len(user1.audit_logs) == 1

    # Test Document.tenant and Document.user relationships
    await db_session.refresh(doc1, ["tenant", "user"])
    assert doc1.tenant.id == tenant.id
    assert doc1.user.id == user1.id
