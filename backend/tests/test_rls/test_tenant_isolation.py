"""
Integration tests for Row-Level Security (RLS) tenant isolation.

Tests verify that RLS policies correctly enforce tenant isolation at the database level,
preventing cross-tenant data access and ensuring data can only be accessed within
the correct tenant context.
"""

import pytest
import uuid
from sqlalchemy import text
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_users(db_session, test_tenants):
    """
    Test that RLS blocks cross-tenant access to users table.

    Verifies that when tenant context is set to tenant1, queries
    only return users belonging to tenant1, even though users
    from tenant2 exist in the database.
    """
    tenant1_id, tenant2_id = test_tenants

    # Create users in both tenants
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())

    await db_session.execute(
        text("""
            INSERT INTO users (id, tenant_id, email, full_name, created_at, updated_at)
            VALUES
                (:user1_id, :tenant1_id, 'user1@tenant1.com', 'User 1', NOW(), NOW()),
                (:user2_id, :tenant2_id, 'user2@tenant2.com', 'User 2', NOW(), NOW())
        """),
        {
            "user1_id": user1_id,
            "tenant1_id": tenant1_id,
            "user2_id": user2_id,
            "tenant2_id": tenant2_id
        }
    )
    await db_session.commit()

    # Set tenant context to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # Query users - should only return tenant1's user
    result = await db_session.execute(text("SELECT id, email FROM users"))
    users = result.fetchall()

    # Verify only tenant1's user is returned
    assert len(users) == 1
    assert users[0].id == user1_id
    assert users[0].email == "user1@tenant1.com"


@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_documents(db_session, test_tenants, test_users):
    """
    Test that RLS blocks cross-tenant access to documents table.

    Verifies that documents are properly isolated by tenant and
    queries only return documents belonging to the current tenant context.
    """
    tenant1_id, tenant2_id = test_tenants
    user1_id, user2_id = test_users

    # Create documents in both tenants
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    await db_session.execute(
        text("""
            INSERT INTO documents
            (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, created_at, updated_at)
            VALUES
                (:doc1_id, :tenant1_id, :user1_id, 'tenant1/doc1.pdf', 'test-bucket',
                 'doc1.pdf', 'completed', NOW(), NOW()),
                (:doc2_id, :tenant2_id, :user2_id, 'tenant2/doc2.pdf', 'test-bucket',
                 'doc2.pdf', 'completed', NOW(), NOW())
        """),
        {
            "doc1_id": doc1_id,
            "tenant1_id": tenant1_id,
            "user1_id": user1_id,
            "doc2_id": doc2_id,
            "tenant2_id": tenant2_id,
            "user2_id": user2_id
        }
    )
    await db_session.commit()

    # Set tenant context to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # Query documents - should only return tenant1's document
    result = await db_session.execute(text("SELECT id, filename FROM documents"))
    documents = result.fetchall()

    # Verify only tenant1's document is returned
    assert len(documents) == 1
    assert documents[0].id == doc1_id
    assert documents[0].filename == "doc1.pdf"


@pytest.mark.asyncio
async def test_rls_blocks_unauthorized_insert(db_session, test_tenants):
    """
    Test that RLS blocks INSERT to different tenant.

    Verifies that when tenant context is set to tenant1, attempts
    to insert records with tenant2's ID are blocked by RLS policies.
    """
    tenant1_id, tenant2_id = test_tenants

    # Set tenant context to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # Try to insert user for tenant2 (should be blocked by RLS)
    user_id = str(uuid.uuid4())

    with pytest.raises(Exception) as exc_info:
        await db_session.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, full_name, created_at, updated_at)
                VALUES (:user_id, :tenant_id, 'unauthorized@tenant2.com', 'Unauthorized User', NOW(), NOW())
            """),
            {"user_id": user_id, "tenant_id": tenant2_id}
        )
        await db_session.commit()

    # Verify the insert failed
    # PostgreSQL raises an error when RLS policy blocks the insert
    assert "new row violates row-level security policy" in str(exc_info.value).lower() or \
           "permission denied" in str(exc_info.value).lower() or \
           "policy" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_rls_allows_same_tenant_access(db_session, test_tenants):
    """
    Test that RLS allows access within same tenant.

    Verifies that operations within the same tenant work correctly
    and RLS policies allow legitimate same-tenant access.
    """
    tenant1_id, tenant2_id = test_tenants

    # Set tenant context to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # Insert user for tenant1 (should succeed)
    user_id = str(uuid.uuid4())
    await db_session.execute(
        text("""
            INSERT INTO users (id, tenant_id, email, full_name, created_at, updated_at)
            VALUES (:user_id, :tenant_id, 'authorized@tenant1.com', 'Authorized User', NOW(), NOW())
        """),
        {"user_id": user_id, "tenant_id": tenant1_id}
    )
    await db_session.commit()

    # Query to verify insert succeeded
    result = await db_session.execute(
        text("SELECT id, email FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    user = result.fetchone()

    # Verify user was created and can be accessed
    assert user is not None
    assert user.id == user_id
    assert user.email == "authorized@tenant1.com"


@pytest.mark.asyncio
async def test_rls_missing_tenant_context_returns_empty(db_session, test_tenants, test_users):
    """
    Test that RLS with missing tenant context returns empty results.

    Verifies that when no tenant context is set (or set to NULL/empty),
    RLS policies correctly return no results rather than leaking data.
    """
    tenant1_id, tenant2_id = test_tenants
    user1_id, user2_id = test_users

    # Insert documents for both tenants
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    # First set a valid tenant context to insert
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    await db_session.execute(
        text("""
            INSERT INTO documents
            (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, created_at, updated_at)
            VALUES (:doc_id, :tenant_id, :user_id, 'test/doc.pdf', 'test-bucket', 'doc.pdf', 'completed', NOW(), NOW())
        """),
        {"doc_id": doc1_id, "tenant_id": tenant1_id, "user_id": user1_id}
    )
    await db_session.commit()

    # Now clear tenant context (set to empty string)
    await db_session.execute(text("SET LOCAL app.current_tenant_id = ''"))

    # Query documents with no tenant context - should return empty
    result = await db_session.execute(text("SELECT id FROM documents"))
    documents = result.fetchall()

    # Verify no documents are returned
    assert len(documents) == 0


@pytest.mark.asyncio
async def test_rls_works_with_soft_deleted_records(db_session, test_tenants, test_users):
    """
    Test that RLS policies work correctly with soft-deleted records.

    Verifies that RLS tenant isolation still applies to soft-deleted
    records, ensuring deleted records from other tenants remain hidden.
    """
    tenant1_id, tenant2_id = test_tenants
    user1_id, user2_id = test_users

    # Create documents in both tenants, soft-delete one
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())
    deleted_at = datetime.now(timezone.utc)

    # Set tenant context to insert for both tenants
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    await db_session.execute(
        text("""
            INSERT INTO documents
            (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, deleted_at, created_at, updated_at)
            VALUES
                (:doc1_id, :tenant1_id, :user1_id, 'tenant1/active.pdf', 'test-bucket',
                 'active.pdf', 'completed', NULL, NOW(), NOW())
        """),
        {"doc1_id": doc1_id, "tenant1_id": tenant1_id, "user1_id": user1_id}
    )
    await db_session.commit()

    # Switch context to tenant2 and insert a deleted document
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant2_id}
    )

    await db_session.execute(
        text("""
            INSERT INTO documents
            (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, deleted_at, created_at, updated_at)
            VALUES
                (:doc2_id, :tenant2_id, :user2_id, 'tenant2/deleted.pdf', 'test-bucket',
                 'deleted.pdf', 'completed', :deleted_at, NOW(), NOW())
        """),
        {"doc2_id": doc2_id, "tenant2_id": tenant2_id, "user2_id": user2_id, "deleted_at": deleted_at}
    )
    await db_session.commit()

    # Set context back to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # Query all documents (including soft-deleted) - should only see tenant1's
    result = await db_session.execute(
        text("SELECT id, filename, deleted_at FROM documents")
    )
    documents = result.fetchall()

    # Verify only tenant1's document is returned
    assert len(documents) == 1
    assert documents[0].id == doc1_id
    assert documents[0].deleted_at is None

    # Tenant2's soft-deleted document should not be visible
