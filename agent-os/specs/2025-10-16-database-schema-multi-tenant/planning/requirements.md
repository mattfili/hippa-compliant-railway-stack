# Feature 2 Requirements: Database Schema and Multi-Tenant Data Model

## Overview
This document captures the detailed requirements gathered for Feature 2, which establishes the PostgreSQL schema with tenant isolation patterns, pgvector extension setup, core tables, and database migrations framework.

---

## 1. Multi-Tenancy Pattern

**Decision**: Shared schema with row-level tenant isolation + defense-in-depth enhancements

**Rationale**:
- Operational simplicity: migrations, schema changes, cross-tenant analytics are simpler
- Can fortify row-level isolation with PostgreSQL row-level security (RLS) policies
- Per-tenant encryption keys provide additional protection against cross-tenant data exposure
- Tenant-context middleware and centralized query enforcement logic ensure correct filtering
- Allows future evolution toward stronger isolation if needed (e.g., split high-risk customers)

**Defense-in-Depth Guardrails**:
1. **RLS / DB-level policy enforcement**: Use PostgreSQL's row_level_security so queries without tenant_id filters are rejected
2. **ORM / Data Access Wrapper**: Central data-access API that automatically injects tenant filters
3. **Audit / Monitoring / Alerts**: Monitor for cross-tenant query patterns
4. **Least Privilege DB roles**: Limit direct DB access; application layer handles most queries
5. **Regression / fuzz testing**: Assert no query leaks data across tenants
6. **Keying & encryption**: Ensure sensitive columns require correct tenant context for decryption
7. **Logical partitions / indexing**: Use partitioning (PARTITION BY tenant_id) to reduce performance interference

---

## 2. Tenants Table Schema

**Columns**:
- `id` (UUID, primary key)
- `name` (VARCHAR, not null)
- `status` (VARCHAR, e.g., 'active', 'suspended')
- `kms_key_arn` (VARCHAR, for Feature 4 - per-tenant encryption)
- `created_at` (TIMESTAMPTZ, not null)
- `updated_at` (TIMESTAMPTZ, not null)
- `deleted_at` (TIMESTAMPTZ, nullable - soft delete)
- Possibly `tenant_id` (UUID, FK to self - for multi-level tenancy if needed)

**Notes**:
- Consider adding `max_users`, `max_storage_gb`, `subscription_tier` for future tenant limits
- Soft delete pattern applies

---

## 3. Users Table Schema

**Columns**:
- `id` (UUID, primary key)
- `tenant_id` (UUID, FK to tenants, not null, ON DELETE RESTRICT)
- `email` (VARCHAR, not null)
- `external_idp_id` (VARCHAR, nullable - for linking to authentication provider)
- `full_name` (VARCHAR)
- `role` (VARCHAR - for RBAC in Feature 13)
- `last_login_at` (TIMESTAMPTZ)
- `created_at` (TIMESTAMPTZ, not null)
- `updated_at` (TIMESTAMPTZ, not null)
- `deleted_at` (TIMESTAMPTZ, nullable - soft delete)

**Constraints**:
- `UNIQUE (tenant_id, email) WHERE deleted_at IS NULL` - partial unique index for soft deletes
- Foreign key: `tenant_id` references `tenants(id)` ON DELETE RESTRICT

**Notes**:
- Soft deletes ensure historical references remain intact
- Partial unique index allows email reuse after soft deletion

---

## 4. Documents Table Schema

**Columns**:
- `id` (UUID, primary key)
- `tenant_id` (UUID, FK to tenants, not null, ON DELETE RESTRICT)
- `user_id` (UUID, FK to users, not null, ON DELETE RESTRICT - uploader)
- `s3_key` (VARCHAR, not null)
- `s3_bucket` (VARCHAR, not null)
- `filename` (VARCHAR, not null)
- `content_type` (VARCHAR)
- `size_bytes` (BIGINT)
- `status` (VARCHAR - 'processing', 'completed', 'failed')
- `metadata` (JSONB - custom attributes)
- `embedding_vector` (VECTOR(1024), nullable - for pgvector)
- `created_at` (TIMESTAMPTZ, not null)
- `updated_at` (TIMESTAMPTZ, not null)
- `deleted_at` (TIMESTAMPTZ, nullable - soft delete)

**Constraints**:
- Foreign keys:
  - `tenant_id` references `tenants(id)` ON DELETE RESTRICT
  - `user_id` references `users(id)` ON DELETE RESTRICT

**Notes**:
- `embedding_vector` is nullable initially (documents uploaded before embeddings generated)
- Embeddings live directly in documents table (no separate chunks table for now)
- JSONB metadata allows flexible custom attributes

---

## 5. Document Chunks

**Decision**: Embeddings live directly in the documents table

**Rationale**:
- Simplifies initial schema
- Can evolve to separate chunks table in future features if needed
- Single vector per document is sufficient for MVP

---

## 6. Audit Logs Table Schema

**Columns**:
- `id` (UUID, primary key)
- `tenant_id` (UUID, FK to tenants, not null)
- `user_id` (UUID, FK to users, nullable)
- `action` (VARCHAR, not null - e.g., "document.uploaded", "user.created")
- `resource_type` (VARCHAR, not null)
- `resource_id` (UUID, not null)
- `ip_address` (INET)
- `user_agent` (TEXT)
- `metadata` (JSONB - additional context)
- `created_at` (TIMESTAMPTZ, not null)
- Optionally: `previous_hash` or `chain_hash` (VARCHAR - for tamper-evidence)

**Immutability Requirements**:
1. **Append-only**: Disallow normal UPDATE or DELETE operations via ORM or API (only INSERT)
2. **DB-side constraints**:
   - Use PostgreSQL RLS or table-level policies to prevent UPDATE/DELETE by non-admin roles
   - Grant only minimal permissions to application database roles
   - Optionally create triggers that reject any UPDATE/DELETE (raise exception)
3. **Tamper-evidence** (optional):
   - Add `previous_hash` column: compute SHA256(previous_hash || current_row_data)
   - On query/audit, recompute and verify chain is unbroken
4. **External immutable log copy**: Stream audit rows to external append-only log store as backup
5. **Performance**:
   - Index on `tenant_id`, `user_id`, `action`, `created_at`
   - Consider partitioning by time (monthly) for scalability
6. **Testing**: Write tests that try (and fail) to UPDATE/DELETE audit rows

**Notes**:
- If retraction needed, insert new "redaction" record rather than modifying existing row
- Periodic integrity checks to detect tampering

---

## 7. pgvector Configuration

**Embedding Dimensions**: 1024 (matching Titan Embeddings V2)

**Column Type**: `VECTOR(1024)`

**Indexing**: HNSW indexes for fast similarity search

**Index Parameters**: Use default parameters for `m` and `ef_construction` (no specific preference)

**Target Columns**:
- `documents.embedding_vector`

**Example Index**:
```sql
CREATE INDEX idx_documents_embedding_hnsw
ON documents
USING hnsw (embedding_vector vector_cosine_ops);
```

---

## 8. Vector Column Nullability

**Decision**: Vector columns should be **nullable** initially

**Rationale**:
- Documents are uploaded before embeddings are generated (async processing)
- Allows document records to be created immediately upon upload
- Embedding generation happens in background processing pipeline

---

## 9. Indexing Strategy

**Required Indexes**:
1. `tenants(id)` - primary key (automatic)
2. `users(tenant_id, email)` - tenant-scoped user lookup (partial unique index WHERE deleted_at IS NULL)
3. `documents(tenant_id, created_at)` - recent documents per tenant
4. `documents(tenant_id, user_id)` - user's documents
5. `audit_logs(tenant_id, created_at)` - recent audit events
6. `audit_logs(user_id, created_at)` - user activity audit
7. `audit_logs(action)` - audit queries by action type
8. HNSW index on `documents(embedding_vector)` for similarity search

**Additional Considerations**:
- Composite indexes should list tenant_id first for tenant-scoped queries
- Consider partitioning by `tenant_id` for large-scale deployments
- Monitor query patterns and add indexes as needed

---

## 10. Foreign Key Constraints & Soft Deletes

**Foreign Key Strategy**:
- **Critical relationships** (tenants → users, tenants → documents): Use `ON DELETE RESTRICT` (or default `NO ACTION`)
  - Prevents accidental deletion of tenant wiping all data
  - Forces explicit handling of tenant deletion
- **Dependent data** (documents → chunks, if chunks existed): Use `ON DELETE CASCADE`
  - Only when child data is truly subordinate and never useful in isolation
  - Beware: large cascades can have performance/transactional costs

**Soft Delete Strategy**:
- **Strongly preferred** for all domain entities in audit/compliance systems
- Add `deleted_at` (TIMESTAMPTZ, nullable) to all main tables
- Benefits:
  - Preserve historical state and references
  - Avoid accidental data loss
  - Enable undeletion/reconciliation
  - Maintain audit log integrity (can still reference deleted entities)
- Implementation:
  - Use `ON DELETE RESTRICT` for schema constraints
  - Implement soft delete at application layer
  - Background archival/purge job for retention enforcement (with logging)

**Recommendation**: Use soft deletes by default. Use `ON DELETE RESTRICT` for critical parent-child relationships. If cascade delete needed, couple with soft delete or tightly controlled logic.

---

## 11. Unique Constraints

**Decision**: Enforce uniqueness at database level

**Example**:
```sql
ALTER TABLE users
  ADD CONSTRAINT unique_tenant_email
  UNIQUE (tenant_id, email);
```

**For Soft Deletes**: Use partial unique index:
```sql
CREATE UNIQUE INDEX unique_tenant_email_active
  ON users (tenant_id, email)
  WHERE deleted_at IS NULL;
```

**Rationale**:
- Database-level constraints prevent race conditions (parallel signups bypassing app checks)
- Last line of defense against bugs
- Application-level checks still valuable for friendly error messages
- Partial index ensures soft-deleted users don't block email reuse

---

## 12. HIPAA Timestamp Requirements

**Timezone-Aware Timestamps**:
- Use `TIMESTAMPTZ` (not `TIMESTAMP`) for all timestamp columns
- Important for distributed systems and auditing (absolute time with offset)

**Required Timestamp Columns** (all entities):
- `created_at` (TIMESTAMPTZ, not null)
- `updated_at` (TIMESTAMPTZ, not null)
- `deleted_at` (TIMESTAMPTZ, nullable - for soft deletes)

**Optional**:
- `archived_at` (TIMESTAMPTZ) - for multi-phase lifecycle
- `purged_at` (TIMESTAMPTZ) - for retention enforcement

**Benefits**:
- `deleted_at` provides audit trail visibility (when something was tombstoned)
- Enables logical filtering (`WHERE deleted_at IS NULL` for active records)
- Supports HIPAA retention requirements

---

## 13. Migration Strategy

**Approach**: Multiple focused migrations (preferred over one large migration)

**Migration Sequence**:
1. **Migration 1**: Enable pgvector extension (if not already done in Feature 1)
   - Reference existing: `backend/alembic/versions/20251015_1506_1ef269d5fac7_enable_pgvector_extension.py`
2. **Migration 2**: Create tenants table
   - Include RLS policies
   - Include seed data for system tenant
3. **Migration 3**: Create users table with FK to tenants
   - Include RLS policies
   - Include partial unique index
4. **Migration 4**: Create documents table with FKs to tenants/users
   - Include RLS policies
   - Include vector column
5. **Migration 5**: Create audit_logs table
   - Include immutability triggers
   - Include RLS policies
6. **Migration 6**: Create all indexes
   - HNSW index on embedding_vector
   - Composite indexes for tenant-scoped queries
   - Audit log indexes
7. **Migration 7**: Enable RLS on all tables

**Benefits**:
- Easier to review and test
- Clearer git history
- Simpler rollback if issues arise
- Can pause between migrations if needed

---

## 14. Seed Data

**Decision**: Include seed data in migrations

**Required Seed Data**:
- **System tenant**:
  - ID: `00000000-0000-0000-0000-000000000000`
  - Name: "System"
  - Status: "active"
  - Purpose: System-level operations, background jobs, administrative tasks

**Implementation**: Include in Migration 2 (tenants table creation)

---

## 15. Scope Boundaries

**In Scope for Feature 2**:
- All tables mentioned above (tenants, users, documents, audit_logs)
- pgvector extension setup and vector columns
- RLS policies for tenant isolation
- Indexes for tenant-scoped queries
- Migration framework setup
- Seed data for system tenant

**NOT in Scope** (deferred to later features):
- RBAC tables (roles, permissions) - Feature 13
- Encryption key management tables - Feature 4
- Document chunks table (if separate table needed) - Future feature
- PHI detection/scrubbing - Feature 14
- Anomaly detection - Feature 16

---

## Existing Code to Reuse

**Reference Patterns in backend/**:**
- Existing database models or base classes with timestamp mixins
- Existing Alembic migration templates: `backend/alembic/versions/20251015_1506_1ef269d5fac7_enable_pgvector_extension.py`
- SQLAlchemy configuration or session management patterns
- Existing tenant-scoped query helpers or decorators

---

## Visual Assets

**Status**: None provided

**Future Consideration**: ER diagrams could be generated after schema implementation to document relationships

---

## Defense-in-Depth Implementation Checklist

### Database Level
- [ ] Enable Row-Level Security (RLS) on all tables
- [ ] Create RLS policies that enforce tenant_id filtering
- [ ] Grant minimal permissions to application database roles
- [ ] Create triggers to prevent UPDATE/DELETE on audit_logs
- [ ] Implement soft deletes with deleted_at column
- [ ] Add partial unique indexes for soft-deleted records

### Application Level
- [ ] Central data-access API that injects tenant filters
- [ ] ORM/repository layer prevents raw SQL bypassing filters
- [ ] Audit logging for all CRUD operations
- [ ] Monitoring for cross-tenant query patterns

### Testing Level
- [ ] Unit tests for RLS policies
- [ ] Integration tests for tenant isolation
- [ ] Fuzz tests to detect cross-tenant leaks
- [ ] Tests that verify UPDATE/DELETE fails on audit_logs

### Operational Level
- [ ] Monitor audit logs for suspicious patterns
- [ ] Alerts for cross-tenant access attempts
- [ ] Regular integrity checks on audit log hash chains
- [ ] External backup of audit logs to immutable storage

---

## Summary

This feature establishes a secure, auditable, multi-tenant database schema with:
- **4 core tables**: tenants, users, documents, audit_logs
- **Row-level isolation** with defense-in-depth (RLS, soft deletes, audit logging)
- **pgvector support** for 1024-dimensional embeddings
- **HIPAA compliance**: timestamptz, soft deletes, append-only audit logs
- **7 focused migrations** for clear change management
- **Seed data** for system tenant
- **Comprehensive indexing** for tenant-scoped query performance

The schema is designed to support Feature 5 (document ingestion), Feature 7 (embeddings), Feature 8 (vector search), and Feature 10 (audit logging) while maintaining strict tenant isolation and HIPAA compliance requirements.
