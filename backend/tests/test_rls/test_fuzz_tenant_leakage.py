"""
Fuzz tests for detecting tenant data leakage in RLS policies.

These tests use randomized data and scenarios to detect edge cases
where tenant isolation might be compromised.
"""

import pytest
import uuid
import asyncio
from sqlalchemy import text


@pytest.mark.asyncio
async def test_fuzz_many_tenants_no_leakage(db_session):
    """
    Test 10 tenants with 5 documents each for data leakage.

    Creates a large dataset across multiple tenants and verifies
    that each tenant can only access their own documents, with
    no cross-tenant data leakage.
    """
    # Create 10 tenants
    tenant_ids = [str(uuid.uuid4()) for _ in range(10)]

    # Insert tenants
    for tenant_id in tenant_ids:
        await db_session.execute(
            text("""
                INSERT INTO tenants (id, name, status, created_at, updated_at)
                VALUES (:tenant_id, :name, 'active', NOW(), NOW())
            """),
            {"tenant_id": tenant_id, "name": f"Tenant {tenant_id[:8]}"}
        )

    # Create one user per tenant
    user_ids = {}
    for tenant_id in tenant_ids:
        user_id = str(uuid.uuid4())
        user_ids[tenant_id] = user_id

        await db_session.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, full_name, created_at, updated_at)
                VALUES (:user_id, :tenant_id, :email, :name, NOW(), NOW())
            """),
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "email": f"user@{tenant_id[:8]}.com",
                "name": f"User {tenant_id[:8]}"
            }
        )

    await db_session.commit()

    # Create 5 documents per tenant (50 total documents)
    document_map = {}  # Map tenant_id -> list of doc_ids

    for tenant_id in tenant_ids:
        document_map[tenant_id] = []
        user_id = user_ids[tenant_id]

        for i in range(5):
            doc_id = str(uuid.uuid4())
            document_map[tenant_id].append(doc_id)

            # Set tenant context before inserting
            await db_session.execute(
                text("SET LOCAL app.current_tenant_id = :tenant_id"),
                {"tenant_id": tenant_id}
            )

            await db_session.execute(
                text("""
                    INSERT INTO documents
                    (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, created_at, updated_at)
                    VALUES
                        (:doc_id, :tenant_id, :user_id, :s3_key, 'test-bucket',
                         :filename, 'completed', NOW(), NOW())
                """),
                {
                    "doc_id": doc_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "s3_key": f"tenant/{tenant_id}/doc{i}.pdf",
                    "filename": f"document_{i}.pdf"
                }
            )

        await db_session.commit()

    # Verify each tenant can only see their own documents
    for tenant_id in tenant_ids:
        # Set tenant context
        await db_session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )

        # Query documents
        result = await db_session.execute(
            text("SELECT id, s3_key FROM documents ORDER BY s3_key")
        )
        documents = result.fetchall()

        # Should see exactly 5 documents
        assert len(documents) == 5, \
            f"Tenant {tenant_id[:8]} should see 5 documents, saw {len(documents)}"

        # All documents should belong to this tenant
        doc_ids_seen = [doc.id for doc in documents]
        expected_doc_ids = set(document_map[tenant_id])
        actual_doc_ids = set(doc_ids_seen)

        assert actual_doc_ids == expected_doc_ids, \
            f"Tenant {tenant_id[:8]} saw wrong documents. " \
            f"Expected {expected_doc_ids}, got {actual_doc_ids}"

        # All s3_keys should start with this tenant's prefix
        for doc in documents:
            assert doc.s3_key.startswith(f"tenant/{tenant_id}"), \
                f"Document {doc.id} has wrong s3_key: {doc.s3_key}"


@pytest.mark.asyncio
async def test_fuzz_concurrent_tenant_queries(db_session, test_tenants, test_users):
    """
    Test concurrent queries from different tenants.

    Simulates multiple tenants querying simultaneously to ensure
    RLS context isolation works correctly under concurrent load.
    """
    tenant1_id, tenant2_id = test_tenants
    user1_id, user2_id = test_users

    # Create documents for both tenants
    tenant1_docs = []
    tenant2_docs = []

    # Create 10 documents for each tenant
    for i in range(10):
        doc1_id = str(uuid.uuid4())
        doc2_id = str(uuid.uuid4())
        tenant1_docs.append(doc1_id)
        tenant2_docs.append(doc2_id)

        # Insert for tenant1
        await db_session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant1_id}
        )

        await db_session.execute(
            text("""
                INSERT INTO documents
                (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, created_at, updated_at)
                VALUES (:doc_id, :tenant_id, :user_id, :s3_key, 'test-bucket', :filename, 'completed', NOW(), NOW())
            """),
            {
                "doc_id": doc1_id,
                "tenant_id": tenant1_id,
                "user_id": user1_id,
                "s3_key": f"tenant1/doc{i}.pdf",
                "filename": f"doc{i}.pdf"
            }
        )
        await db_session.commit()

        # Insert for tenant2
        await db_session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant2_id}
        )

        await db_session.execute(
            text("""
                INSERT INTO documents
                (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, created_at, updated_at)
                VALUES (:doc_id, :tenant_id, :user_id, :s3_key, 'test-bucket', :filename, 'completed', NOW(), NOW())
            """),
            {
                "doc_id": doc2_id,
                "tenant_id": tenant2_id,
                "user_id": user2_id,
                "s3_key": f"tenant2/doc{i}.pdf",
                "filename": f"doc{i}.pdf"
            }
        )
        await db_session.commit()

    # Simulate concurrent queries by alternating tenant contexts rapidly
    for _ in range(5):  # Run 5 iterations
        # Query as tenant1
        await db_session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant1_id}
        )
        result1 = await db_session.execute(text("SELECT id FROM documents"))
        docs1 = [row.id for row in result1.fetchall()]

        # Query as tenant2
        await db_session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant2_id}
        )
        result2 = await db_session.execute(text("SELECT id FROM documents"))
        docs2 = [row.id for row in result2.fetchall()]

        # Verify correct isolation
        assert len(docs1) == 10, f"Tenant1 should see 10 docs, saw {len(docs1)}"
        assert len(docs2) == 10, f"Tenant2 should see 10 docs, saw {len(docs2)}"

        # Verify no overlap
        assert set(docs1).isdisjoint(set(docs2)), \
            "Tenant documents leaked across tenant boundary"

        # Verify correct documents
        assert set(docs1) == set(tenant1_docs), \
            "Tenant1 saw wrong documents"
        assert set(docs2) == set(tenant2_docs), \
            "Tenant2 saw wrong documents"


@pytest.mark.asyncio
async def test_fuzz_tenant_id_manipulation(db_session, test_tenants, test_users):
    """
    Test that RLS prevents tenant_id manipulation in queries.

    Attempts to bypass RLS by manipulating tenant_id in WHERE clauses
    and verifies that RLS still enforces proper isolation.
    """
    tenant1_id, tenant2_id = test_tenants
    user1_id, user2_id = test_users

    # Create documents for both tenants
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    await db_session.execute(
        text("""
            INSERT INTO documents
            (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, created_at, updated_at)
            VALUES (:doc_id, :tenant_id, :user_id, 'tenant1/doc.pdf', 'test-bucket', 'doc.pdf', 'completed', NOW(), NOW())
        """),
        {"doc_id": doc1_id, "tenant_id": tenant1_id, "user_id": user1_id}
    )
    await db_session.commit()

    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant2_id}
    )

    await db_session.execute(
        text("""
            INSERT INTO documents
            (id, tenant_id, user_id, s3_key, s3_bucket, filename, status, created_at, updated_at)
            VALUES (:doc_id, :tenant_id, :user_id, 'tenant2/doc.pdf', 'test-bucket', 'doc.pdf', 'completed', NOW(), NOW())
        """),
        {"doc_id": doc2_id, "tenant_id": tenant2_id, "user_id": user2_id}
    )
    await db_session.commit()

    # Set context to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # Attempt 1: Try to query with explicit tenant_id = tenant2_id in WHERE
    result = await db_session.execute(
        text("SELECT id FROM documents WHERE tenant_id = :tenant2_id"),
        {"tenant2_id": tenant2_id}
    )
    docs = result.fetchall()
    # RLS should still block access - should return empty
    assert len(docs) == 0, "RLS should block cross-tenant access even with explicit WHERE"

    # Attempt 2: Try to query with OR condition
    result = await db_session.execute(
        text("""
            SELECT id FROM documents
            WHERE tenant_id = :tenant1_id OR tenant_id = :tenant2_id
        """),
        {"tenant1_id": tenant1_id, "tenant2_id": tenant2_id}
    )
    docs = result.fetchall()
    # Should only return tenant1's document
    assert len(docs) == 1, "RLS should only allow tenant1's documents"
    assert docs[0].id == doc1_id

    # Attempt 3: Try to use UNION to combine results
    result = await db_session.execute(
        text("""
            SELECT id FROM documents WHERE tenant_id = :tenant1_id
            UNION ALL
            SELECT id FROM documents WHERE tenant_id = :tenant2_id
        """),
        {"tenant1_id": tenant1_id, "tenant2_id": tenant2_id}
    )
    docs = result.fetchall()
    # RLS should still apply to both parts of UNION
    assert len(docs) == 1, "RLS should apply to UNION queries"
    assert docs[0].id == doc1_id


@pytest.mark.asyncio
async def test_audit_log_rls_allows_insert_select_only(db_session, test_tenants, test_users):
    """
    Test that audit log RLS allows only INSERT and SELECT.

    Verifies that audit logs have separate INSERT and SELECT policies,
    and that UPDATE/DELETE are blocked (in addition to trigger enforcement).
    """
    tenant1_id, tenant2_id = test_tenants
    user1_id, user2_id = test_users

    # Set context to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # INSERT should succeed for tenant1
    audit1_id = str(uuid.uuid4())
    resource_id = str(uuid.uuid4())

    await db_session.execute(
        text("""
            INSERT INTO audit_logs
            (id, tenant_id, user_id, action, resource_type, resource_id, metadata, created_at)
            VALUES
                (:audit_id, :tenant_id, :user_id, 'document.created', 'document',
                 :resource_id, '{}', NOW())
        """),
        {
            "audit_id": audit1_id,
            "tenant_id": tenant1_id,
            "user_id": user1_id,
            "resource_id": resource_id
        }
    )
    await db_session.commit()

    # SELECT should return the audit log
    result = await db_session.execute(
        text("SELECT id, action FROM audit_logs WHERE id = :audit_id"),
        {"audit_id": audit1_id}
    )
    audit = result.fetchone()
    assert audit is not None
    assert audit.id == audit1_id
    assert audit.action == "document.created"

    # Create audit log for tenant2
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant2_id}
    )

    audit2_id = str(uuid.uuid4())
    await db_session.execute(
        text("""
            INSERT INTO audit_logs
            (id, tenant_id, user_id, action, resource_type, resource_id, metadata, created_at)
            VALUES
                (:audit_id, :tenant_id, :user_id, 'user.login', 'user',
                 :resource_id, '{}', NOW())
        """),
        {
            "audit_id": audit2_id,
            "tenant_id": tenant2_id,
            "user_id": user2_id,
            "resource_id": user2_id
        }
    )
    await db_session.commit()

    # Switch back to tenant1 context
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # SELECT should not return tenant2's audit logs (RLS isolation)
    result = await db_session.execute(
        text("SELECT id FROM audit_logs WHERE id = :audit_id"),
        {"audit_id": audit2_id}
    )
    audit = result.fetchone()
    assert audit is None, "RLS should block access to other tenant's audit logs"

    # SELECT should return all tenant1 logs
    result = await db_session.execute(text("SELECT id FROM audit_logs"))
    audits = result.fetchall()
    assert len(audits) == 1
    assert audits[0].id == audit1_id

    # UPDATE should fail (trigger + RLS enforcement)
    with pytest.raises(Exception) as exc_info:
        await db_session.execute(
            text("UPDATE audit_logs SET action = 'modified' WHERE id = :audit_id"),
            {"audit_id": audit1_id}
        )
        await db_session.commit()

    # Verify update was blocked
    assert "immutable" in str(exc_info.value).lower() or \
           "cannot" in str(exc_info.value).lower() or \
           "trigger" in str(exc_info.value).lower()

    await db_session.rollback()

    # DELETE should fail (trigger + RLS enforcement)
    with pytest.raises(Exception) as exc_info:
        await db_session.execute(
            text("DELETE FROM audit_logs WHERE id = :audit_id"),
            {"audit_id": audit1_id}
        )
        await db_session.commit()

    # Verify delete was blocked
    assert "immutable" in str(exc_info.value).lower() or \
           "cannot" in str(exc_info.value).lower() or \
           "trigger" in str(exc_info.value).lower()
