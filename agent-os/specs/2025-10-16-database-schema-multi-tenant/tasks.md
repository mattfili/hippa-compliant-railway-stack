# Task Breakdown: Database Schema and Multi-Tenant Data Model

## Overview

**Total Tasks:** 34 tasks across 6 phases
**Estimated Total Effort:** 40 hours (1 week for one developer)
**Assigned Implementers:** database-engineer, testing-engineer

## Critical Path Summary

The critical path flows sequentially through phases 1-6:
1. **Base Models & Mixins** - Enhances Base model with soft delete support
2. **Database Migrations** - Creates all 7 migrations for tables, indexes, and RLS
3. **SQLAlchemy Models** - Creates 4 models (Tenant, User, Document, AuditLog)
4. **Row-Level Security Testing** - Validates tenant isolation at database level
5. **Audit Log Immutability Testing** - Validates append-only enforcement
6. **Documentation** - Documents schema, RLS patterns, and extension points

**Key Dependencies:**
- Phase 1 (Base Models) blocks all other phases
- Phase 2 (Migrations) blocks Phase 3 (SQLAlchemy Models)
- Phase 3 (Models) blocks Phase 4-5 (Testing)
- Phase 6 (Documentation) can start early but finalizes at end

---

## Phase 1: Base Models & Soft Delete Support

**Phase Goal:** Enhance Base model with soft delete support and create tenant-scoped mixin

### Task Group 1: Enhanced Base Model with Soft Deletes
**Assigned implementer:** database-engineer
**Dependencies:** None (builds on Feature 1's existing Base model)
**Estimated Effort:** 3 hours

- [x] 1.0 Enhance Base model with soft delete support
  - [x] 1.1 Write 4 focused tests for soft delete functionality
    - Test soft_delete() method sets deleted_at timestamp
    - Test restore() method clears deleted_at timestamp
    - Test is_deleted property returns correct boolean
    - Test is_active property returns correct boolean
    - Create `backend/tests/test_models/test_soft_delete.py`
  - [x] 1.2 Create SoftDeleteMixin class
    - Update `backend/app/database/base.py`
    - Add `deleted_at: Mapped[datetime | None]` column (TIMESTAMPTZ, nullable)
    - Add `@hybrid_property is_deleted` (Python + SQL expression)
    - Add `@hybrid_property is_active` (Python + SQL expression)
    - Add `soft_delete()` method to set deleted_at = NOW()
    - Add `restore()` method to clear deleted_at
    - Add `active_query()` classmethod returning query with WHERE deleted_at IS NULL
    - Add `deleted_query()` classmethod returning query with WHERE deleted_at IS NOT NULL
  - [x] 1.3 Ensure soft delete tests pass
    - Run ONLY the 4 tests written in 1.1
    - Verify soft_delete() sets timestamp correctly
    - Verify restore() clears timestamp correctly
    - Do NOT run the entire test suite at this stage

**Deliverables:**
- Updated `backend/app/database/base.py` (SoftDeleteMixin added)
- `backend/tests/test_models/test_soft_delete.py` (4 focused tests)

**Acceptance Criteria:**
- The 4 tests written in 1.1 pass
- SoftDeleteMixin provides hybrid properties for Python and SQL
- active_query() and deleted_query() return correct filters
- Mixin can be applied to any model class

**References:**
- Spec section: "Soft Deletes" (lines 464-526)
- Existing base model: `backend/app/database/base.py`

---

## Phase 2: Database Migrations

**Phase Goal:** Create all 7 migrations for tables, indexes, RLS policies, and seed data

### Task Group 2: Table Migrations (Migrations 2-5)
**Assigned implementer:** database-engineer
**Dependencies:** Task Group 1
**Estimated Effort:** 8 hours

- [x] 2.0 Create core table migrations
  - [x] 2.1 Create Migration 2: Tenants table with RLS and seed data
    - Run `alembic revision -m "create_tenants_table"`
    - Create tenants table with columns: id, name, status, kms_key_arn, created_at, updated_at, deleted_at
    - Add table and column comments
    - Create indexes: idx_tenants_status (partial WHERE deleted_at IS NULL), idx_tenants_deleted_at (partial WHERE deleted_at IS NOT NULL)
    - Seed system tenant with id='00000000-0000-0000-0000-000000000000', name='System', status='active'
    - Implement downgrade() to drop table
    - Reference spec lines 646-726
  - [x] 2.2 Create Migration 3: Users table with FK to tenants and RLS
    - Run `alembic revision -m "create_users_table"`
    - Create users table with columns: id, tenant_id, email, external_idp_id, full_name, role, last_login_at, created_at, updated_at, deleted_at
    - Add FK constraint: tenant_id references tenants(id) ON DELETE RESTRICT
    - Add table and column comments
    - Create partial unique index: idx_users_tenant_email_active ON (tenant_id, email) WHERE deleted_at IS NULL
    - Create composite index: idx_users_tenant_created ON (tenant_id, created_at DESC)
    - Create index: idx_users_external_idp ON (external_idp_id) WHERE external_idp_id IS NOT NULL AND deleted_at IS NULL
    - Implement downgrade() to drop table
    - Reference spec lines 728-809
  - [x] 2.3 Create Migration 4: Documents table with FKs and vector column
    - Run `alembic revision -m "create_documents_table"`
    - Create documents table with columns: id, tenant_id, user_id, s3_key, s3_bucket, filename, content_type, size_bytes, status, metadata (JSONB), embedding_vector (VECTOR(1024)), created_at, updated_at, deleted_at
    - Add FK constraints: tenant_id references tenants(id), user_id references users(id) (both ON DELETE RESTRICT)
    - Add CHECK constraint: status IN ('processing', 'completed', 'failed')
    - Add table and column comments
    - Create composite indexes: idx_documents_tenant_created, idx_documents_tenant_user, idx_documents_tenant_status (partial WHERE deleted_at IS NULL)
    - Create JSONB GIN index: idx_documents_metadata_gin
    - Implement downgrade() to drop table
    - Reference spec lines 811-906
  - [x] 2.4 Create Migration 5: Audit logs table with immutability triggers
    - Run `alembic revision -m "create_audit_logs_table"`
    - Create audit_logs table with columns: id, tenant_id, user_id, action, resource_type, resource_id, ip_address (INET), user_agent, metadata (JSONB), created_at
    - Note: NO updated_at or deleted_at columns (append-only)
    - Add FK constraints: tenant_id references tenants(id), user_id references users(id) (both ON DELETE RESTRICT, user_id nullable)
    - Add table and column comments
    - Create trigger function prevent_audit_log_modification() that raises exception
    - Create triggers: prevent_audit_log_update (BEFORE UPDATE), prevent_audit_log_delete (BEFORE DELETE)
    - Create indexes: idx_audit_logs_tenant_created, idx_audit_logs_user_created (partial WHERE user_id IS NOT NULL), idx_audit_logs_action, idx_audit_logs_resource
    - Create JSONB GIN index: idx_audit_logs_metadata_gin
    - Implement downgrade() to drop triggers, function, and table
    - Reference spec lines 908-1032
  - [x] 2.5 Verify table migrations run successfully
    - Run `alembic upgrade head` from clean database
    - Verify all 4 tables created with correct columns and types
    - Verify system tenant seed data inserted
    - Verify foreign key constraints exist
    - Verify triggers on audit_logs prevent UPDATE/DELETE
    - Run `alembic downgrade base` to test reversibility
    - Run `alembic upgrade head` again to restore state

**Deliverables:**
- `backend/alembic/versions/[timestamp]_create_tenants_table.py` (Migration 2)
- `backend/alembic/versions/[timestamp]_create_users_table.py` (Migration 3)
- `backend/alembic/versions/[timestamp]_create_documents_table.py` (Migration 4)
- `backend/alembic/versions/[timestamp]_create_audit_logs_table.py` (Migration 5)

**Acceptance Criteria:**
- All 4 migrations run successfully with `alembic upgrade head`
- Tables created with correct columns, types, and constraints
- System tenant seed data exists with id='00000000-0000-0000-0000-000000000000'
- Foreign key constraints use ON DELETE RESTRICT
- Audit log triggers prevent UPDATE and DELETE operations
- All migrations are reversible with `alembic downgrade`

**References:**
- Spec section: "Migrations" (lines 625-1178)
- Existing pgvector migration: `backend/alembic/versions/20251015_1506_1ef269d5fac7_enable_pgvector_extension.py`

### Task Group 3: Index and RLS Migrations (Migrations 6-7)
**Assigned implementer:** database-engineer
**Dependencies:** Task Group 2
**Estimated Effort:** 4 hours

- [x] 3.0 Create vector index and RLS migrations
  - [x] 3.1 Create Migration 6: HNSW vector index
    - Run `alembic revision -m "create_vector_indexes"`
    - Create HNSW index: idx_documents_embedding_hnsw USING hnsw (embedding_vector vector_cosine_ops)
    - Use partial index: WHERE embedding_vector IS NOT NULL AND deleted_at IS NULL
    - Add comments explaining HNSW parameters (m=16, ef_construction=64 defaults)
    - Implement downgrade() to drop index
    - Reference spec lines 1034-1077
  - [x] 3.2 Create Migration 7: Enable Row-Level Security policies
    - Run `alembic revision -m "enable_row_level_security"`
    - Enable RLS on tenants table, create tenant_isolation_policy (FOR ALL USING id = current_setting('app.current_tenant_id')::uuid)
    - Enable RLS on users table, create user_isolation_policy (FOR ALL USING tenant_id = current_setting('app.current_tenant_id')::uuid)
    - Enable RLS on documents table, create document_isolation_policy (FOR ALL USING tenant_id = current_setting('app.current_tenant_id')::uuid)
    - Enable RLS on audit_logs table, create audit_log_select_policy (FOR SELECT) and audit_log_insert_policy (FOR INSERT)
    - Use NULLIF(current_setting('app.current_tenant_id', true), '')::uuid for safe missing variable handling
    - Implement downgrade() to drop policies and disable RLS
    - Reference spec lines 1079-1178
  - [x] 3.3 Verify index and RLS migrations
    - Run `alembic upgrade head` to apply migrations
    - Verify HNSW index exists on documents.embedding_vector
    - Verify RLS enabled on all 4 tables
    - Verify RLS policies exist and are active
    - Test downgrade and re-upgrade for reversibility

**Deliverables:**
- `backend/alembic/versions/[timestamp]_create_vector_indexes.py` (Migration 6)
- `backend/alembic/versions/[timestamp]_enable_row_level_security.py` (Migration 7)

**Acceptance Criteria:**
- HNSW index created on embedding_vector column
- RLS enabled on all 4 tables (tenants, users, documents, audit_logs)
- RLS policies enforce tenant_id filtering using current_setting
- Audit logs have separate SELECT and INSERT policies (no UPDATE/DELETE)
- Migrations are reversible

**References:**
- Spec section: "Row-Level Security (RLS)" (lines 376-463)
- Spec section: "Migrations" (lines 1034-1178)

---

## Phase 3: SQLAlchemy Models

**Phase Goal:** Create SQLAlchemy models for all 4 tables with relationships and helper methods

### Task Group 4: Core Domain Models
**Assigned implementer:** database-engineer
**Dependencies:** Task Groups 1-3
**Estimated Effort:** 6 hours

- [x] 4.0 Create SQLAlchemy models for all tables
  - [x] 4.1 Write 6 focused tests for model functionality
    - Test Tenant model creation and soft delete
    - Test User model with tenant relationship and partial unique index
    - Test Document model with vector similarity search
    - Test AuditLog model append-only enforcement
    - Test model relationships (Tenant.users, User.documents, etc.)
    - Test soft delete allows email reuse (partial unique index)
    - Create `backend/tests/test_models/test_models.py`
  - [x] 4.2 Create Tenant model
    - Create `backend/app/models/tenant.py`
    - Inherit from Base and SoftDeleteMixin
    - Add columns: name, status, kms_key_arn
    - Add relationships: users, documents, audit_logs (with cascade="save-update, merge", passive_deletes=True)
    - Add __repr__ method
    - Reference spec lines 1286-1348
  - [x] 4.3 Create User model
    - Create `backend/app/models/user.py`
    - Inherit from Base and SoftDeleteMixin
    - Add columns: tenant_id (FK), email, external_idp_id, full_name, role, last_login_at
    - Add relationships: tenant, documents, audit_logs
    - Add __repr__ method
    - Reference spec lines 1350-1432
  - [x] 4.4 Create Document model with vector search
    - Create `backend/app/models/document.py`
    - Inherit from Base and SoftDeleteMixin
    - Add columns: tenant_id (FK), user_id (FK), s3_key, s3_bucket, filename, content_type, size_bytes, status, metadata (JSONB), embedding_vector (VECTOR(1024))
    - Add relationships: tenant, user
    - Add similarity_search() classmethod for vector similarity search using cosine distance
    - Add __repr__ method
    - Reference spec lines 1434-1568
  - [x] 4.5 Create AuditLog model (append-only)
    - Create `backend/app/models/audit_log.py`
    - Inherit from Base only (NOT SoftDeleteMixin)
    - Override updated_at to None (no update timestamp on append-only table)
    - Add columns: tenant_id (FK), user_id (FK, nullable), action, resource_type, resource_id, ip_address (INET), user_agent, metadata (JSONB)
    - Add relationships: tenant, user
    - Add create() classmethod as the ONLY way to create audit logs
    - Do NOT expose update() or delete() methods
    - Add __repr__ method
    - Reference spec lines 1570-1678
  - [x] 4.6 Create models index
    - Create `backend/app/models/__init__.py`
    - Import and export all 4 models: Tenant, User, Document, AuditLog
    - Add module docstring explaining model patterns
    - Reference spec lines 1680-1706
  - [ ] 4.7 Ensure model tests pass
    - Run ONLY the 6 tests written in 4.1
    - Verify models create records correctly
    - Verify relationships work correctly
    - Verify soft delete allows email reuse
    - Do NOT run the entire test suite at this stage

**Deliverables:**
- `backend/app/models/tenant.py` (Tenant model)
- `backend/app/models/user.py` (User model)
- `backend/app/models/document.py` (Document model with vector search)
- `backend/app/models/audit_log.py` (AuditLog model, append-only)
- `backend/app/models/__init__.py` (models index)
- `backend/tests/test_models/test_models.py` (6 focused tests)

**Acceptance Criteria:**
- The 6 tests written in 4.1 pass
- All 4 models created with correct columns and types
- Relationships defined with appropriate cascade behaviors
- Document.similarity_search() returns results ordered by cosine distance
- AuditLog only exposes create() method (no update or delete)
- Soft delete mixin applied to Tenant, User, Document (but NOT AuditLog)

**References:**
- Spec section: "SQLAlchemy Models" (lines 1180-1706)
- Existing Base model: `backend/app/database/base.py`

---

## Phase 4: Row-Level Security Testing

**Phase Goal:** Validate tenant isolation at database level with RLS integration tests

### Task Group 5: RLS Integration Tests
**Assigned implementer:** testing-engineer
**Dependencies:** Task Group 4
**Estimated Effort:** 5 hours

- [x] 5.0 Write integration tests for Row-Level Security
  - [x] 5.1 Review RLS implementation and identify test scenarios
    - Review Migration 7 RLS policies in `backend/alembic/versions/[timestamp]_enable_row_level_security.py`
    - Review tenant context middleware in `backend/app/middleware/tenant_context.py`
    - Identify critical RLS scenarios: tenant isolation, cross-tenant blocking, policy enforcement
  - [x] 5.2 Write RLS tenant isolation tests (maximum 6 tests)
    - Create `backend/tests/test_rls/test_tenant_isolation.py`
    - Test RLS blocks cross-tenant access to users table
    - Test RLS blocks cross-tenant access to documents table
    - Test RLS blocks unauthorized INSERT to different tenant
    - Test RLS allows access within same tenant
    - Test RLS with missing tenant context returns empty results
    - Test RLS policies work with soft-deleted records
  - [x] 5.3 Write RLS fuzz tests (maximum 4 tests)
    - Create `backend/tests/test_rls/test_fuzz_tenant_leakage.py`
    - Test 10 tenants with 5 documents each, verify no cross-tenant leaks
    - Test concurrent queries from different tenants don't leak data
    - Test RLS policies prevent tenant_id manipulation in queries
    - Test audit log RLS allows only INSERT and SELECT (no UPDATE/DELETE)
  - [x] 5.4 Create RLS test fixtures
    - Update `backend/tests/conftest.py`
    - Add fixture for setting tenant context: set_tenant_context(db_session, tenant_id)
    - Add fixture for creating test tenants with users and documents
    - Add fixture for clearing tenant context
  - [ ] 5.5 Run RLS integration tests
    - Run ONLY the 10 tests written in 5.2 and 5.3
    - Verify tenant isolation enforced at database level
    - Verify cross-tenant access blocked by RLS policies
    - Do NOT run the entire test suite at this stage

**Deliverables:**
- `backend/tests/test_rls/test_tenant_isolation.py` (6 RLS isolation tests)
- `backend/tests/test_rls/test_fuzz_tenant_leakage.py` (4 fuzz tests)
- Updated `backend/tests/conftest.py` (RLS test fixtures)

**Acceptance Criteria:**
- All 10 RLS tests pass
- Tests verify tenant isolation at database level
- Tests verify RLS blocks cross-tenant access attempts
- Fuzz tests detect no tenant data leakage
- Tests verify audit log RLS allows only INSERT and SELECT

**References:**
- Spec section: "Row-Level Security (RLS)" (lines 376-463)
- Spec section: "Testing Strategy" (lines 1745-1985)

---

## Phase 5: Audit Log Immutability Testing

**Phase Goal:** Validate audit log append-only enforcement with trigger tests

### Task Group 6: Audit Log Immutability Tests
**Assigned implementer:** testing-engineer
**Dependencies:** Task Group 4
**Estimated Effort:** 3 hours


- [x] 6.0 Write tests for audit log immutability
  - [x] 6.1 Review audit log implementation and identify test scenarios
    - Review Migration 5 immutability triggers in `backend/alembic/versions/[timestamp]_create_audit_logs_table.py`
    - Review AuditLog model in `backend/app/models/audit_log.py`
    - Identify critical immutability scenarios: INSERT allowed, UPDATE blocked, DELETE blocked
  - [x] 6.2 Write audit log immutability tests (maximum 6 tests)
    - Create `backend/tests/test_audit/test_audit_log_immutability.py`
    - Test AuditLog.create() successfully inserts record
    - Test direct UPDATE on audit_logs table raises exception
    - Test direct DELETE on audit_logs table raises exception
    - Test ORM-level update attempt raises exception
    - Test ORM-level delete attempt raises exception
    - Test audit log SELECT queries work correctly with tenant scoping
  - [x] 6.3 Create audit log test fixtures
    - Update `backend/tests/conftest.py`
    - Add fixture for creating test audit logs
    - Add fixture for verifying audit log record count doesn't decrease
  - [x] 6.4 Run audit log immutability tests
    - Run ONLY the 6 tests written in 6.2
    - Verify INSERT allowed via AuditLog.create()
    - Verify UPDATE and DELETE blocked by database triggers
    - Do NOT run the entire test suite at this stage
**Deliverables:**
- `backend/tests/test_audit/test_audit_log_immutability.py` (6 immutability tests)
- Updated `backend/tests/conftest.py` (audit log test fixtures)

**Acceptance Criteria:**
- All 6 audit log immutability tests pass
- Tests verify INSERT allowed via AuditLog.create()
- Tests verify UPDATE and DELETE raise exceptions
- Tests verify database triggers enforce immutability
- Tests verify audit log queries work with tenant scoping

**References:**
- Spec section: "Audit Log Immutability" (lines 536-622)
- Spec section: "Testing Strategy" (lines 1956-1985)

---

## Phase 6: Documentation

**Phase Goal:** Document schema, RLS patterns, model usage, and extension points for future features

### Task Group 7: Schema and Extension Documentation
**Assigned implementer:** database-engineer
**Dependencies:** Task Groups 1-6
**Estimated Effort:** 5 hours

- [ ] 7.0 Create comprehensive schema documentation
  - [ ] 7.1 Create DATABASE_SCHEMA.md
    - Create `backend/docs/DATABASE_SCHEMA.md`
    - Document all 4 tables with column descriptions and data types
    - Include ER diagram (text-based or Mermaid syntax)
    - Document all indexes with their purposes
    - Document all foreign key relationships and ON DELETE behaviors
    - Document pgvector configuration (1024 dimensions, HNSW index parameters)
    - Document soft delete pattern and partial unique indexes
    - Document audit log append-only pattern
    - Reference spec lines 108-327
  - [ ] 7.2 Create RLS_PATTERNS.md
    - Create `backend/docs/RLS_PATTERNS.md`
    - Explain Row-Level Security architecture
    - Document how to set tenant context: `SET LOCAL app.current_tenant_id = '...'`
    - Document RLS policy patterns for each table
    - Show example queries with RLS enforcement
    - Document how to test RLS policies
    - Document defense-in-depth layers: RLS + application filtering + middleware + audit logs
    - Add troubleshooting guide for RLS issues
    - Reference spec lines 376-463
  - [ ] 7.3 Create MODEL_USAGE.md
    - Create `backend/docs/MODEL_USAGE.md`
    - Document how to use soft delete mixin (soft_delete(), restore(), is_active)
    - Document how to query with active_query() and deleted_query()
    - Document vector similarity search with Document.similarity_search()
    - Document audit log creation with AuditLog.create()
    - Show example code for common CRUD operations
    - Document model relationships and how to use them
    - Document JSONB metadata field usage
    - Reference spec lines 1180-1706
  - [ ] 7.4 Create EXTENSION_POINTS.md
    - Create `backend/docs/EXTENSION_POINTS.md`
    - Document extension points for Feature 4 (per-tenant encryption with kms_key_arn)
    - Document extension points for Feature 5 (document ingestion with s3_key, s3_bucket)
    - Document extension points for Feature 7 (embedding generation with embedding_vector)
    - Document extension points for Feature 8 (vector search with similarity_search())
    - Document extension points for Feature 10 (audit logging with AuditLog.create())
    - Document extension points for Feature 13 (RBAC with role column)
    - Show example code for each extension point
    - Reference spec lines 2174-2272
  - [ ] 7.5 Update backend README.md
    - Update `backend/README.md`
    - Add section on database schema and migrations
    - Document how to run migrations: `alembic upgrade head`
    - Document how to create new migrations: `alembic revision -m "description"`
    - Link to new documentation files (DATABASE_SCHEMA.md, RLS_PATTERNS.md, MODEL_USAGE.md, EXTENSION_POINTS.md)
    - Document seed data (system tenant)
    - Document multi-tenancy architecture

**Deliverables:**
- `backend/docs/DATABASE_SCHEMA.md` (schema reference)
- `backend/docs/RLS_PATTERNS.md` (RLS implementation guide)
- `backend/docs/MODEL_USAGE.md` (model usage examples)
- `backend/docs/EXTENSION_POINTS.md` (future feature integration)
- Updated `backend/README.md` (migration instructions)

**Acceptance Criteria:**
- DATABASE_SCHEMA.md documents all tables, columns, indexes, and relationships
- RLS_PATTERNS.md explains how to use and test RLS policies
- MODEL_USAGE.md provides clear examples for common operations
- EXTENSION_POINTS.md shows integration points for future features
- README.md updated with migration instructions and architecture overview

**References:**
- Spec sections: "Tables Design" (lines 108-327), "Row-Level Security" (lines 376-463), "SQLAlchemy Models" (lines 1180-1706), "Extension Points" (lines 2174-2272)

---

## Task Group 7: Railway Integration & Template Metadata

**Phase:** 7
**Implementer:** database-engineer
**Estimated Effort:** 4 hours
**Dependencies:** Phase 2 (migrations must exist), Phase 6 (documentation complete)

**Purpose:** Create Railway template metadata and verify PostgreSQL configuration for one-click deployment.

- [x] 7.0 Railway Integration & Template Metadata
  - [x] 7.1 Create template.json for Railway template publishing
    - Created `template.json` with 2 services (PostgreSQL, backend)
    - Defined 8 environment variables with descriptions
    - Added HIPAA compliance notes in instructions
    - Validated JSON syntax
  - [x] 7.2 Verify pgvector Extension Configuration
    - Updated pgvector migration with verification check
    - Created `backend/docs/RAILWAY_SETUP.md` with manual verification steps
    - Added comprehensive troubleshooting guide
  - [x] 7.3 Document PostgreSQL Configuration Tuning
    - Created `backend/docs/POSTGRESQL_TUNING.md`
    - Documented production performance optimization commands
    - Documented HIPAA compliance settings (WAL archiving)
    - Documented backup configuration steps
    - Documented connection limits by Railway plan
  - [x] 7.4 Update README with Railway Deployment Instructions
    - Updated `backend/README.md` with Railway deployment section
    - Added pgvector template deployment steps
    - Documented environment variable configuration
    - Added deployment verification steps
    - Added HIPAA compliance checklist
    - Linked to RAILWAY_SETUP.md and POSTGRESQL_TUNING.md

---

**Objective:** Create `template.json` for Railway template publishing with all services, environment variables, and setup instructions.

**Steps:**
1. Create `template.json` in repository root
2. Define PostgreSQL service using `pgvector/pgvector:pg15` image
3. Define backend service with health check configuration
4. Document all required environment variables with descriptions
5. Add deployment instructions and HIPAA compliance notes

**Implementation:**
```bash
# Create template.json
touch template.json
```

Copy template.json content from spec.md (lines 2221-2320).

**Testing:**
- Validate JSON syntax with `jq . template.json`
- Verify all environment variables from backend are included
- Confirm health check path matches railway.json

**Deliverables:**
- `template.json` in repository root

**Acceptance Criteria:**
- Valid JSON format
- PostgreSQL service uses pgvector/pgvector:pg15 image
- Backend service references correct repository and directory
- All 8 required environment variables documented with descriptions
- Deployment instructions include HIPAA compliance notes

**References:**
- Spec section: "Railway Configuration" (lines 2124-2320)

---

### Task 7.2: Verify pgvector Extension Configuration

**Objective:** Document and verify pgvector extension is properly enabled in PostgreSQL.

**Steps:**
1. Add pgvector verification to Migration 1 (or create new verification migration)
2. Document manual verification steps in `backend/docs/RAILWAY_SETUP.md`
3. Add troubleshooting guide for extension issues

**Implementation:**
Update existing pgvector migration or create verification script:

```python
# backend/alembic/versions/<existing>_enable_pgvector_extension.py

def upgrade():
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Verify extension is available
    connection = op.get_bind()
    result = connection.execute(
        text("SELECT * FROM pg_available_extensions WHERE name = 'vector'")
    ).fetchone()

    if not result:
        raise Exception(
            "pgvector extension not available. "
            "Please ensure Railway PostgreSQL uses pgvector/pgvector image. "
            "See: https://railway.com/deploy/3jJFCA"
        )
```

**Testing:**
- Run migration against Railway PostgreSQL instance
- Verify extension enabled: `SELECT * FROM pg_extension WHERE extname = 'vector';`
- Test vector operations work: `SELECT '[1,2,3]'::vector;`

**Deliverables:**
- Updated pgvector migration with verification
- `backend/docs/RAILWAY_SETUP.md` with verification steps

**Acceptance Criteria:**
- Migration verifies pgvector availability
- Documentation includes manual verification steps
- Troubleshooting guide for common extension issues

**References:**
- Spec section: "Railway Configuration" (lines 2126-2142)
- Railway pgvector template: https://railway.com/deploy/3jJFCA

---

### Task 7.3: Document PostgreSQL Configuration Tuning

**Objective:** Create documentation for optimizing Railway PostgreSQL performance and HIPAA compliance.

**Steps:**
1. Create `backend/docs/POSTGRESQL_TUNING.md`
2. Document ALTER SYSTEM commands for production workloads
3. Document backup configuration steps
4. Document connection limit considerations by Railway plan

**Implementation:**
Create comprehensive PostgreSQL tuning guide:

```markdown
# PostgreSQL Configuration Tuning for Railway

## Production Performance Optimization

For production workloads with 8GB RAM, apply these settings:

\`\`\`sql
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET max_connections = '100';
\`\`\`

Restart PostgreSQL service in Railway dashboard after changes.

## HIPAA Compliance Settings

Enable WAL archiving for audit trail:

\`\`\`sql
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET archive_mode = 'on';
\`\`\`

## Backup Configuration

1. Navigate to PostgreSQL service in Railway dashboard
2. Enable "Backups" feature
3. Configure retention: 30+ days (HIPAA requirement)
4. Verify backup schedule
5. Test restoration process

## Connection Limits by Plan

Railway PostgreSQL connection limits:
- Free/Hobby: ~20-50 connections
- Pro: 100+ connections

Application uses 20 connections (pool_size=10 + max_overflow=10).

Monitor connection usage:
\`\`\`sql
SELECT count(*) FROM pg_stat_activity;
\`\`\`
```

**Testing:**
- Apply tuning commands to test Railway instance
- Verify settings: `SHOW shared_buffers;`, `SHOW effective_cache_size;`
- Test backup/restore process

**Deliverables:**
- `backend/docs/POSTGRESQL_TUNING.md`

**Acceptance Criteria:**
- Production tuning commands documented
- HIPAA compliance settings documented
- Backup configuration steps included
- Connection limit guidance by Railway plan

**References:**
- Spec section: "Railway Configuration" (lines 2189-2215)

---

### Task 7.4: Update README with Railway Deployment Instructions

**Objective:** Add Railway-specific deployment section to main README.

**Steps:**
1. Update `backend/README.md` with Railway deployment section
2. Add pgvector template usage instructions
3. Document environment variable setup
4. Link to RAILWAY_SETUP.md and POSTGRESQL_TUNING.md

**Implementation:**
Add Railway section to README.md:

```markdown
## Railway Deployment

### Using Railway Template (Recommended)

1. **Deploy pgvector PostgreSQL template:**
   - Visit: https://railway.com/deploy/3jJFCA
   - Click "Deploy Now"
   - Wait for PostgreSQL provisioning

2. **Deploy this application:**
   - Fork this repository
   - Connect to Railway from dashboard
   - Select "backend" directory as root
   - Configure environment variables (see below)

3. **Configure Environment Variables:**
   Required variables:
   - `DATABASE_URL` - Auto-provided by Railway PostgreSQL service
   - `ALLOWED_ORIGINS` - Your frontend URLs (comma-separated)
   - `OIDC_ISSUER_URL` - Your IdP issuer URL
   - `OIDC_CLIENT_ID` - Your IdP client ID
   - `OIDC_CLIENT_SECRET` - Your IdP client secret
   - `AWS_REGION` - AWS region for Bedrock/KMS
   - `AWS_ACCESS_KEY_ID` - AWS credentials
   - `AWS_SECRET_ACCESS_KEY` - AWS credentials

4. **Verify Deployment:**
   - Check health endpoint: `https://<your-url>/api/v1/health/ready`
   - Verify migrations ran: Check Railway logs for "Database migrations completed"
   - Verify pgvector: See docs/RAILWAY_SETUP.md

### HIPAA Compliance Checklist

Before storing PHI data:
- [ ] Sign Railway Business Associate Agreement (BAA)
- [ ] Enable encryption at rest on PostgreSQL
- [ ] Enable Railway Backups (30+ day retention)
- [ ] Configure PostgreSQL tuning (see docs/POSTGRESQL_TUNING.md)
- [ ] Verify RLS policies enabled (see docs/RLS_PATTERNS.md)

For detailed setup instructions, see:
- [Railway Setup Guide](docs/RAILWAY_SETUP.md)
- [PostgreSQL Tuning](docs/POSTGRESQL_TUNING.md)
```

**Testing:**
- Follow README instructions on clean Railway account
- Verify all links work
- Confirm environment variables list is complete

**Deliverables:**
- Updated `backend/README.md` with Railway section

**Acceptance Criteria:**
- Railway deployment instructions are clear and complete
- pgvector template usage documented
- Environment variables list matches template.json
- HIPAA compliance checklist included
- Links to Railway setup docs work

**References:**
- Spec section: "Railway Configuration" (lines 2124-2320)
- Existing `backend/README.md`

---

## Summary & Execution Notes

### Phase Dependencies
```
Phase 1 (Base Models & Mixins)
    ↓
Phase 2 (Database Migrations)
    ↓
Phase 3 (SQLAlchemy Models)
    ↓
Phase 4 (RLS Integration Tests) + Phase 5 (Audit Log Tests)
    ↓
Phase 6 (Documentation)
    ↓
Phase 7 (Railway Integration)
```

### Parallel Work Opportunities
- **Phase 4 & 5** can be worked on in parallel (RLS tests + Audit log tests)
- **Phase 6** documentation can start early and continue throughout
- **Phase 7** can begin after Phase 2 completes (migrations exist)

### Critical Path Highlights
1. **Base Models (Phase 1)** - Foundation for all models
2. **Migrations (Phase 2)** - Creates database schema
3. **SQLAlchemy Models (Phase 3)** - Enables application data access
4. **RLS Testing (Phase 4)** - Validates tenant isolation
5. **Audit Testing (Phase 5)** - Validates immutability
6. **Documentation (Phase 6)** - Enables future feature development
7. **Railway Integration (Phase 7)** - Enables template publishing and one-click deployment

### Implementer Assignment Summary
- **database-engineer**: 5 task groups (Phases 1-3, 6-7) - 30 hours
- **testing-engineer**: 2 task groups (Phases 4-5) - 8 hours

### Estimated Effort Breakdown by Phase
- **Phase 1:** 3 hours (Base Models & Mixins)
- **Phase 2:** 12 hours (7 Migrations)
- **Phase 3:** 6 hours (4 SQLAlchemy Models)
- **Phase 4:** 5 hours (RLS Integration Tests)
- **Phase 5:** 3 hours (Audit Log Immutability Tests)
- **Phase 6:** 5 hours (Documentation)
- **Phase 7:** 4 hours (Railway Integration & Template Metadata)

**Total Estimated Effort:** 38 hours (approximately 5 working days)

### Test Coverage Summary
Following the minimal testing approach from Feature 1:
- **Phase 1:** 4 soft delete tests
- **Phase 3:** 6 model tests
- **Phase 4:** 10 RLS integration tests
- **Phase 5:** 6 audit log immutability tests

**Total Expected Tests:** 26 tests maximum (focused on critical workflows only)

### Success Criteria Checklist
- [ ] All 7 migrations run successfully with `alembic upgrade head`
- [ ] System tenant seed data exists with id='00000000-0000-0000-0000-000000000000'
- [ ] All 4 SQLAlchemy models created with relationships
- [ ] SoftDeleteMixin applied to Tenant, User, Document (but NOT AuditLog)
- [ ] HNSW index created on documents.embedding_vector
- [ ] RLS policies enabled on all 4 tables
- [ ] All 26 tests pass (4 soft delete + 6 model + 10 RLS + 6 audit)
- [ ] Audit log UPDATE and DELETE blocked by database triggers
- [ ] Partial unique index allows email reuse after soft deletion
- [ ] Vector similarity search returns results ordered by distance
- [ ] All 5 documentation files complete and accurate
- [ ] template.json created with valid JSON and all services defined
- [ ] pgvector extension verification in migrations
- [ ] Railway deployment documentation complete (RAILWAY_SETUP.md, POSTGRESQL_TUNING.md)
- [ ] README.md updated with Railway deployment instructions

### Out of Scope Reminders
Not included in Feature 2:
- RBAC tables (roles, permissions, role_assignments) - Feature 13
- Encryption key management tables - Feature 4
- Document chunks table (separate from documents) - Future feature
- PHI detection/scrubbing logic - Feature 14
- Anomaly detection tables - Feature 16
- API endpoints for CRUD operations - Future features
- Document ingestion API - Feature 5
- Embedding generation logic - Feature 7
- Vector search API endpoints - Feature 8
- Audit log API endpoints - Feature 10

### Migration File Naming Convention
Following Alembic defaults:
- Format: `YYYYMMDD_HHMM_<revision_id>_<description>.py`
- Example: `20251016_1400_a1b2c3d4e5f6_create_tenants_table.py`
- Revision IDs are auto-generated by Alembic

### Railway Configuration Notes
Feature 2 includes Railway integration work in Phase 7:
- **template.json** - Template metadata for Railway publishing (Task 7.1)
- **pgvector verification** - Ensure extension is available (Task 7.2)
- **PostgreSQL tuning docs** - Performance and HIPAA configuration (Task 7.3)
- **README updates** - Deployment instructions (Task 7.4)

Requirements for Railway deployment:
- PostgreSQL version 15+ (for pgvector support)
- Use pgvector template: https://railway.com/deploy/3jJFCA
- DATABASE_URL environment variable (auto-provided by Railway)
- All application environment variables configured (see template.json)

### Next Steps After Completion
Feature 2 establishes the foundation for:
- **Feature 4:** Per-Tenant Encryption (uses kms_key_arn column in tenants table)
- **Feature 5:** Document Ingestion API (uses Document model with s3_key, s3_bucket)
- **Feature 7:** Embedding Generation (uses embedding_vector column in documents table)
- **Feature 8:** Vector Search API (uses Document.similarity_search() method)
- **Feature 10:** Audit Logging API (uses AuditLog model)
- **Feature 13:** Authorization & RBAC (uses role column in users table)

All future features will build on the multi-tenant data model and RLS patterns established in Feature 2.

### Standards Compliance
This tasks list follows all user standards:
- **Backend Models:** Clear naming, timestamps, data integrity constraints, appropriate data types, indexes on foreign keys
- **Backend Migrations:** Reversible migrations, small focused changes, separate schema and data, clear naming conventions
- **Testing:** Minimal tests during development (26 tests total), test only core user flows, defer edge case testing
- **Multi-Tenancy:** Shared schema with row-level isolation, defense-in-depth (RLS + application filtering + middleware + audit logs)
- **HIPAA Compliance:** Timezone-aware timestamps (TIMESTAMPTZ), soft deletes for retention, immutable audit logs, per-tenant encryption support
