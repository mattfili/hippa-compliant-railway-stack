# Specification: Database Schema and Multi-Tenant Data Model

## Goal

Establish a secure, auditable, HIPAA-compliant multi-tenant PostgreSQL database schema with tenant isolation, pgvector support for RAG embeddings, and defense-in-depth security layers including Row-Level Security (RLS), soft deletes, and append-only audit logging.

## User Stories

- As a platform operator, I want tenant data strictly isolated so that one organization's data can never leak to another organization
- As a compliance officer, I want immutable audit logs of all database operations so that I can prove HIPAA compliance during audits
- As a developer, I want clear SQLAlchemy models with tenant-scoping mixins so that I can safely build features without risking cross-tenant data leaks
- As a data scientist, I want vector embeddings stored efficiently so that I can perform semantic search across documents within a tenant's scope
- As a system administrator, I want soft deletes on all entities so that accidental deletions can be recovered and audit trails remain intact

## Core Requirements

### Functional Requirements

- Four core tables: tenants, users, documents, audit_logs
- Multi-tenant row-level isolation with PostgreSQL RLS policies
- Soft delete support with deleted_at timestamp on all domain entities
- pgvector support for 1024-dimensional embeddings (Titan Embeddings V2)
- Append-only audit log table with immutability enforcement
- System tenant seed data for administrative operations
- Comprehensive indexing strategy for tenant-scoped queries and vector search
- Seven focused Alembic migrations for incremental schema deployment

### Non-Functional Requirements

- HIPAA compliance: timezone-aware timestamps (TIMESTAMPTZ) on all tables
- Database-level constraints prevent cross-tenant access attempts
- Partial unique indexes support soft deletes without blocking email reuse
- HNSW vector indexes provide sub-second similarity search
- ON DELETE RESTRICT for critical relationships to prevent accidental data loss
- All migrations must be reversible with proper downgrade() implementations
- Performance: Composite indexes list tenant_id first for partition pruning

## Visual Design

No mockups provided. This is a backend database schema feature.

## Reusable Components

### Existing Code to Leverage

**Base Model Pattern:**
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/database/base.py` - DeclarativeBase with UUID id, created_at, updated_at
- Existing pattern uses `String(36)` for UUID storage
- Automatic timestamp management with `func.now()` and `onupdate`
- `to_dict()` helper method for serialization

**Database Engine:**
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/database/engine.py` - Async SQLAlchemy engine with connection pooling
- Connection retry logic with exponential backoff
- Session factory with proper lifecycle management
- `get_session()` FastAPI dependency pattern

**Migration Framework:**
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/alembic/env.py` - Async Alembic configuration
- Automatic DATABASE_URL conversion for asyncpg
- Base metadata import for autogenerate support
- Existing pgvector extension migration: `backend/alembic/versions/20251015_1506_1ef269d5fac7_enable_pgvector_extension.py`

**Tenant Context Infrastructure:**
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/middleware/tenant_context.py` - Tenant context middleware
- `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/auth/tenant_extractor.py` - JWT tenant claim extraction
- Logging context integration with `tenant_id_ctx`

### New Components Required

**Soft Delete Mixin:**
- Add `deleted_at` column to Base or create SoftDeleteMixin
- Hybrid property `is_deleted` for easy filtering
- Scoped queries that automatically filter `WHERE deleted_at IS NULL`

**Tenant-Scoped Mixin:**
- `tenant_id` foreign key column
- Validation that tenant_id is always set on tenant-scoped models
- Helper methods for tenant-scoped queries

**Vector Column Support:**
- pgvector Vector type integration with SQLAlchemy
- Custom column type for VECTOR(1024)
- Similarity search helper methods (cosine, L2, inner product)

**Audit Log Model:**
- Immutability enforcement via database triggers
- JSONB metadata field for flexible audit context
- Hash chain support (optional) for tamper detection

## Technical Approach

### Database Architecture

**Multi-Tenancy Strategy:**
- Shared database, shared schema with row-level isolation
- Every tenant-scoped table has `tenant_id UUID NOT NULL`
- PostgreSQL Row-Level Security (RLS) enforces tenant filtering at database level
- Application layer also filters by tenant_id (defense-in-depth)

**Defense-in-Depth Layers:**
1. Database RLS policies reject queries without tenant_id filtering
2. SQLAlchemy models include tenant_id in all tenant-scoped queries
3. Middleware extracts and validates tenant_id from JWT
4. Audit logging tracks all data access attempts
5. Integration tests verify tenant isolation with fuzz testing

### Tables Design

#### 1. Tenants Table

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    kms_key_arn VARCHAR(512),  -- For Feature 4: per-tenant encryption
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Index for active tenant lookups
CREATE INDEX idx_tenants_status ON tenants(status) WHERE deleted_at IS NULL;

-- Index for soft delete filtering
CREATE INDEX idx_tenants_deleted_at ON tenants(deleted_at) WHERE deleted_at IS NOT NULL;
```

**Columns:**
- `id`: UUID primary key
- `name`: Organization name (255 char max)
- `status`: Enum-like varchar ('active', 'suspended', 'trial')
- `kms_key_arn`: AWS KMS key ARN for tenant-specific encryption (Feature 4)
- `created_at`, `updated_at`, `deleted_at`: HIPAA-compliant timestamps

**Future Extensions:**
- `max_users`, `max_storage_gb`, `subscription_tier` for tenant quotas
- `parent_tenant_id` for hierarchical multi-tenancy

#### 2. Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    external_idp_id VARCHAR(255),  -- Link to Cognito/OIDC provider
    full_name VARCHAR(255),
    role VARCHAR(50),  -- For Feature 13: RBAC
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT fk_users_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenants(id) ON DELETE RESTRICT
);

-- Partial unique index for soft deletes (allows email reuse after deletion)
CREATE UNIQUE INDEX idx_users_tenant_email_active
    ON users(tenant_id, email)
    WHERE deleted_at IS NULL;

-- Composite index for tenant-scoped user queries
CREATE INDEX idx_users_tenant_created
    ON users(tenant_id, created_at DESC);

-- Index for OIDC provider lookups
CREATE INDEX idx_users_external_idp
    ON users(external_idp_id)
    WHERE external_idp_id IS NOT NULL AND deleted_at IS NULL;
```

**Columns:**
- `id`: UUID primary key
- `tenant_id`: Foreign key to tenants (NOT NULL, ON DELETE RESTRICT)
- `email`: User email address
- `external_idp_id`: External identity provider ID (Cognito sub, Auth0 user_id)
- `full_name`: Display name
- `role`: User role for RBAC (admin, member, viewer)
- `last_login_at`: Last successful login timestamp
- Timestamps: created_at, updated_at, deleted_at

**Constraints:**
- Partial unique index on (tenant_id, email) WHERE deleted_at IS NULL
- Foreign key to tenants with ON DELETE RESTRICT

#### 3. Documents Table

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,  -- Uploader
    s3_key VARCHAR(1024) NOT NULL,
    s3_bucket VARCHAR(255) NOT NULL,
    filename VARCHAR(512) NOT NULL,
    content_type VARCHAR(127),
    size_bytes BIGINT,
    status VARCHAR(50) NOT NULL DEFAULT 'processing',
    metadata JSONB DEFAULT '{}',
    embedding_vector VECTOR(1024),  -- pgvector, nullable
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT fk_documents_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenants(id) ON DELETE RESTRICT,
    CONSTRAINT fk_documents_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT chk_documents_status
        CHECK (status IN ('processing', 'completed', 'failed'))
);

-- Composite index for tenant-scoped document queries (most common)
CREATE INDEX idx_documents_tenant_created
    ON documents(tenant_id, created_at DESC);

-- Index for user's documents
CREATE INDEX idx_documents_tenant_user
    ON documents(tenant_id, user_id, created_at DESC);

-- Index for document status filtering
CREATE INDEX idx_documents_tenant_status
    ON documents(tenant_id, status)
    WHERE deleted_at IS NULL;

-- HNSW index for vector similarity search (cosine distance)
CREATE INDEX idx_documents_embedding_hnsw
    ON documents
    USING hnsw (embedding_vector vector_cosine_ops)
    WHERE embedding_vector IS NOT NULL AND deleted_at IS NULL;

-- JSONB GIN index for metadata queries
CREATE INDEX idx_documents_metadata_gin
    ON documents USING gin(metadata);
```

**Columns:**
- `id`: UUID primary key
- `tenant_id`: Foreign key to tenants (NOT NULL, ON DELETE RESTRICT)
- `user_id`: Foreign key to users - who uploaded (NOT NULL, ON DELETE RESTRICT)
- `s3_key`: S3 object key (1024 char max for deep paths)
- `s3_bucket`: S3 bucket name
- `filename`: Original filename from upload
- `content_type`: MIME type (application/pdf, image/png, etc.)
- `size_bytes`: File size in bytes
- `status`: Processing status (processing, completed, failed)
- `metadata`: JSONB for flexible custom attributes
- `embedding_vector`: VECTOR(1024) for semantic search (nullable)
- Timestamps: created_at, updated_at, deleted_at

**Constraints:**
- Foreign keys to tenants and users with ON DELETE RESTRICT
- Check constraint on status enum values

**Vector Design Decision:**
- Embeddings live directly in documents table (not separate chunks table)
- Simplifies MVP implementation
- Can evolve to document_chunks table in later features if needed
- Vector column is nullable (embeddings generated async after upload)

#### 4. Audit Logs Table

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID,  -- Nullable for system actions
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_audit_logs_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenants(id) ON DELETE RESTRICT,
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE RESTRICT
);

-- Note: No updated_at or deleted_at - audit logs are immutable

-- Composite index for tenant audit queries
CREATE INDEX idx_audit_logs_tenant_created
    ON audit_logs(tenant_id, created_at DESC);

-- Index for user activity auditing
CREATE INDEX idx_audit_logs_user_created
    ON audit_logs(user_id, created_at DESC)
    WHERE user_id IS NOT NULL;

-- Index for action type queries
CREATE INDEX idx_audit_logs_action
    ON audit_logs(action, created_at DESC);

-- Index for resource lookups
CREATE INDEX idx_audit_logs_resource
    ON audit_logs(resource_type, resource_id, created_at DESC);

-- JSONB GIN index for metadata searches
CREATE INDEX idx_audit_logs_metadata_gin
    ON audit_logs USING gin(metadata);
```

**Columns:**
- `id`: UUID primary key
- `tenant_id`: Foreign key to tenants (NOT NULL)
- `user_id`: Foreign key to users (nullable for system actions)
- `action`: Action performed (document.uploaded, user.created, etc.)
- `resource_type`: Type of resource (document, user, tenant)
- `resource_id`: UUID of affected resource
- `ip_address`: Client IP address (INET type)
- `user_agent`: Browser/client user agent
- `metadata`: JSONB for additional context (request_id, changes, etc.)
- `created_at`: Timestamp (NOT NULL, no default updates)

**Immutability Design:**
- No `updated_at` or `deleted_at` columns
- Database triggers prevent UPDATE and DELETE operations
- Application layer only performs INSERT operations
- If retraction needed, insert a new "redaction" record

**Future Extensions:**
- `previous_hash` column for cryptographic hash chain (tamper detection)
- `chain_hash` = SHA256(previous_hash || current_row_data)
- Periodic integrity verification jobs

### Constraints

**Foreign Key Strategy:**
- All foreign keys use `ON DELETE RESTRICT` (prevent cascading deletes)
- Forces explicit handling of entity deletion at application layer
- Preserves referential integrity for audit trails
- Prevents accidental mass deletion via parent entity removal

**Unique Constraints:**
- Partial unique indexes for soft-deleted records
- Example: `CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL`
- Allows email reuse after soft deletion
- Database-level race condition prevention

**Check Constraints:**
- Status enums validated at database level
- Example: `CHECK (status IN ('processing', 'completed', 'failed'))`
- Prevents invalid state transitions
- Defense against application bugs

### Indexes

**Tenant-Scoped Query Indexes:**
- All composite indexes list `tenant_id` first for partition pruning
- DESC ordering on timestamp columns for recent-first queries
- Partial indexes with `WHERE deleted_at IS NULL` for active records only

**Vector Search Indexes:**
- HNSW algorithm for approximate nearest neighbor search
- Cosine distance operator (`vector_cosine_ops`)
- Partial index excludes NULL vectors and deleted documents
- Default parameters (m=16, ef_construction=64)

**JSONB Indexes:**
- GIN indexes on metadata columns for flexible querying
- Supports containment operators (@>, ?, ?&, ?|)
- Enables ad-hoc metadata searches without schema changes

**Performance Considerations:**
- Avoid over-indexing (each index has write cost)
- Monitor pg_stat_user_indexes for unused indexes
- Consider BRIN indexes for large time-series tables (audit_logs)
- Partitioning by tenant_id or created_at for massive scale

### Row-Level Security (RLS)

**RLS Policy Strategy:**

1. Enable RLS on all tables
2. Create permissive policies for application role
3. Create restrictive policies for admin role (if needed)
4. Grant minimal permissions to application database user

**Tenants Table RLS:**

```sql
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Application can only access its own tenant record
CREATE POLICY tenant_isolation_policy ON tenants
    FOR ALL
    TO application_role
    USING (id = current_setting('app.current_tenant_id')::uuid);

-- System role can access all tenants
CREATE POLICY tenant_admin_policy ON tenants
    FOR ALL
    TO admin_role
    USING (true);
```

**Users Table RLS:**

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Users scoped to current tenant
CREATE POLICY user_isolation_policy ON users
    FOR ALL
    TO application_role
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**Documents Table RLS:**

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Documents scoped to current tenant
CREATE POLICY document_isolation_policy ON documents
    FOR ALL
    TO application_role
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**Audit Logs Table RLS:**

```sql
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Audit logs scoped to current tenant (read-only for application)
CREATE POLICY audit_log_isolation_policy ON audit_logs
    FOR SELECT
    TO application_role
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Audit logs can only be inserted (append-only)
CREATE POLICY audit_log_insert_policy ON audit_logs
    FOR INSERT
    TO application_role
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Prevent UPDATE and DELETE via policy
-- Additional triggers below for enforcement
```

**RLS Usage Pattern:**

```python
# In application code, set tenant context before queries
await db.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id})

# Now all queries automatically filtered by RLS
results = await db.execute(select(Document))
```

**Important Notes:**
- RLS provides defense-in-depth, not primary security
- Application should still filter by tenant_id in queries
- RLS catches bugs and prevents accidental cross-tenant access
- System/admin operations may need to bypass RLS (SET role)

### Soft Deletes

**Implementation Approach:**

1. Add `deleted_at TIMESTAMPTZ` to all domain tables
2. Set `deleted_at = NOW()` instead of DELETE operations
3. Filter queries with `WHERE deleted_at IS NULL`
4. Use partial unique indexes for soft-deleted records

**Soft Delete Mixin:**

```python
class SoftDeleteMixin:
    """Mixin for soft delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Soft delete timestamp"
    )

    @hybrid_property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None

    @is_deleted.expression
    def is_deleted(cls):
        """SQL expression for is_deleted."""
        return cls.deleted_at.isnot(None)

    @hybrid_property
    def is_active(self) -> bool:
        """Check if record is active (not deleted)."""
        return self.deleted_at is None

    @is_active.expression
    def is_active(cls):
        """SQL expression for is_active."""
        return cls.deleted_at.is_(None)

    def soft_delete(self) -> None:
        """Soft delete this record."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.deleted_at = None
```

**Query Helpers:**

```python
def get_active_query(model_class):
    """Get base query filtering out soft-deleted records."""
    return select(model_class).where(model_class.deleted_at.is_(None))

def get_deleted_query(model_class):
    """Get base query for soft-deleted records only."""
    return select(model_class).where(model_class.deleted_at.isnot(None))
```

**Partial Unique Index Example:**

```sql
-- Allow email reuse after soft deletion
CREATE UNIQUE INDEX idx_users_tenant_email_active
    ON users(tenant_id, email)
    WHERE deleted_at IS NULL;
```

### Audit Log Immutability

**Database-Level Enforcement:**

**Trigger to Prevent Updates:**

```sql
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable and cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_audit_log_update
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();

CREATE TRIGGER prevent_audit_log_delete
    BEFORE DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();
```

**RLS Enforcement:**

```sql
-- Only allow INSERT on audit_logs
CREATE POLICY audit_log_insert_only ON audit_logs
    FOR INSERT
    TO application_role
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Allow SELECT for audit queries
CREATE POLICY audit_log_select_policy ON audit_logs
    FOR SELECT
    TO application_role
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- No UPDATE or DELETE policies (operations will be denied)
```

**Application Layer:**

```python
class AuditLog(Base):
    """Audit log model - append-only."""

    __tablename__ = "audit_logs"

    # No update() or delete() methods exposed
    # Only create() method available

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "AuditLog":
        """Create audit log entry (append-only)."""
        audit_log = cls(**kwargs)
        db.add(audit_log)
        await db.flush()
        return audit_log
```

**Retraction Pattern:**

If audit log needs correction, insert a new "redaction" record:

```python
# Original log
await AuditLog.create(
    db=db,
    tenant_id=tenant_id,
    action="document.uploaded",
    resource_id=doc_id,
    metadata={"filename": "sensitive.pdf"}
)

# Redaction log (if needed)
await AuditLog.create(
    db=db,
    tenant_id=tenant_id,
    action="audit_log.redacted",
    resource_type="audit_log",
    resource_id=original_audit_log_id,
    metadata={"reason": "Contains PII", "redacted_by": admin_user_id}
)
```

### Migrations

**Migration Sequence:**

1. **Migration 1**: Enable pgvector extension (ALREADY EXISTS)
2. **Migration 2**: Create tenants table with RLS + seed system tenant
3. **Migration 3**: Create users table with FK to tenants + RLS
4. **Migration 4**: Create documents table with FKs + vector column + RLS
5. **Migration 5**: Create audit_logs table with immutability triggers + RLS
6. **Migration 6**: Create all indexes (including HNSW)
7. **Migration 7**: Enable RLS on all tables

**Rationale:**
- Separate migrations for easier review and rollback
- Tables created before indexes for better performance
- RLS enabled last to avoid policy conflicts during setup
- Seed data in table creation migration

**Migration File Naming:**
- Format: `YYYYMMDD_HHMM_<revision>_<description>.py`
- Example: `20251016_1400_a1b2c3d4e5f6_create_tenants_table.py`

**Migration 2: Create Tenants Table**

```python
"""create_tenants_table

Revision ID: a1b2c3d4e5f6
Revises: 1ef269d5fac7
Create Date: 2025-10-16 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '1ef269d5fac7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tenants table with soft delete support."""

    # Create tenants table
    op.execute("""
        CREATE TABLE tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'active',
            kms_key_arn VARCHAR(512),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)

    # Add table comment
    op.execute("""
        COMMENT ON TABLE tenants IS 'Organizations/tenants in the multi-tenant system'
    """)

    # Add column comments
    op.execute("""
        COMMENT ON COLUMN tenants.id IS 'Unique tenant identifier (UUID)';
        COMMENT ON COLUMN tenants.name IS 'Organization name';
        COMMENT ON COLUMN tenants.status IS 'Tenant status (active, suspended, trial)';
        COMMENT ON COLUMN tenants.kms_key_arn IS 'AWS KMS key ARN for tenant-specific encryption';
        COMMENT ON COLUMN tenants.deleted_at IS 'Soft delete timestamp (NULL = active)';
    """)

    # Create indexes
    op.execute("""
        CREATE INDEX idx_tenants_status
        ON tenants(status)
        WHERE deleted_at IS NULL
    """)

    op.execute("""
        CREATE INDEX idx_tenants_deleted_at
        ON tenants(deleted_at)
        WHERE deleted_at IS NOT NULL
    """)

    # Seed system tenant
    op.execute("""
        INSERT INTO tenants (id, name, status, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000000',
            'System',
            'active',
            NOW(),
            NOW()
        )
    """)


def downgrade() -> None:
    """Drop tenants table."""
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
```

**Migration 3: Create Users Table**

```python
"""create_users_table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-16 14:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table with tenant isolation."""

    # Create users table
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            email VARCHAR(255) NOT NULL,
            external_idp_id VARCHAR(255),
            full_name VARCHAR(255),
            role VARCHAR(50),
            last_login_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,

            CONSTRAINT fk_users_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants(id)
                ON DELETE RESTRICT
        )
    """)

    # Add table comment
    op.execute("""
        COMMENT ON TABLE users IS 'User accounts with tenant association'
    """)

    # Add column comments
    op.execute("""
        COMMENT ON COLUMN users.tenant_id IS 'Tenant this user belongs to';
        COMMENT ON COLUMN users.external_idp_id IS 'External identity provider ID (Cognito sub, Auth0 user_id)';
        COMMENT ON COLUMN users.role IS 'User role for RBAC (admin, member, viewer)';
    """)

    # Create partial unique index (allows email reuse after soft delete)
    op.execute("""
        CREATE UNIQUE INDEX idx_users_tenant_email_active
        ON users(tenant_id, email)
        WHERE deleted_at IS NULL
    """)

    # Create composite index for tenant-scoped queries
    op.execute("""
        CREATE INDEX idx_users_tenant_created
        ON users(tenant_id, created_at DESC)
    """)

    # Create index for OIDC provider lookups
    op.execute("""
        CREATE INDEX idx_users_external_idp
        ON users(external_idp_id)
        WHERE external_idp_id IS NOT NULL AND deleted_at IS NULL
    """)


def downgrade() -> None:
    """Drop users table."""
    op.execute("DROP TABLE IF EXISTS users CASCADE")
```

**Migration 4: Create Documents Table**

```python
"""create_documents_table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-10-16 14:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create documents table with pgvector support."""

    # Create documents table
    op.execute("""
        CREATE TABLE documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            user_id UUID NOT NULL,
            s3_key VARCHAR(1024) NOT NULL,
            s3_bucket VARCHAR(255) NOT NULL,
            filename VARCHAR(512) NOT NULL,
            content_type VARCHAR(127),
            size_bytes BIGINT,
            status VARCHAR(50) NOT NULL DEFAULT 'processing',
            metadata JSONB DEFAULT '{}',
            embedding_vector VECTOR(1024),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,

            CONSTRAINT fk_documents_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants(id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_documents_user
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE RESTRICT,
            CONSTRAINT chk_documents_status
                CHECK (status IN ('processing', 'completed', 'failed'))
        )
    """)

    # Add table comment
    op.execute("""
        COMMENT ON TABLE documents IS 'Document metadata and storage references'
    """)

    # Add column comments
    op.execute("""
        COMMENT ON COLUMN documents.user_id IS 'User who uploaded the document';
        COMMENT ON COLUMN documents.s3_key IS 'S3 object key for document storage';
        COMMENT ON COLUMN documents.status IS 'Processing status (processing, completed, failed)';
        COMMENT ON COLUMN documents.metadata IS 'Custom document attributes (JSONB)';
        COMMENT ON COLUMN documents.embedding_vector IS 'Vector embedding for semantic search (1024 dimensions)';
    """)

    # Create composite indexes for tenant-scoped queries
    op.execute("""
        CREATE INDEX idx_documents_tenant_created
        ON documents(tenant_id, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX idx_documents_tenant_user
        ON documents(tenant_id, user_id, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX idx_documents_tenant_status
        ON documents(tenant_id, status)
        WHERE deleted_at IS NULL
    """)

    # Create JSONB GIN index for metadata queries
    op.execute("""
        CREATE INDEX idx_documents_metadata_gin
        ON documents USING gin(metadata)
    """)


def downgrade() -> None:
    """Drop documents table."""
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
```

**Migration 5: Create Audit Logs Table**

```python
"""create_audit_logs_table

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-10-16 14:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_logs table with immutability enforcement."""

    # Create audit_logs table (no updated_at or deleted_at - append-only)
    op.execute("""
        CREATE TABLE audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            user_id UUID,
            action VARCHAR(255) NOT NULL,
            resource_type VARCHAR(100) NOT NULL,
            resource_id UUID NOT NULL,
            ip_address INET,
            user_agent TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_audit_logs_tenant
                FOREIGN KEY (tenant_id)
                REFERENCES tenants(id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_audit_logs_user
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE RESTRICT
        )
    """)

    # Add table comment
    op.execute("""
        COMMENT ON TABLE audit_logs IS 'Immutable audit log of all system operations'
    """)

    # Add column comments
    op.execute("""
        COMMENT ON COLUMN audit_logs.user_id IS 'User who performed action (NULL for system actions)';
        COMMENT ON COLUMN audit_logs.action IS 'Action performed (e.g., document.uploaded, user.created)';
        COMMENT ON COLUMN audit_logs.resource_type IS 'Type of resource affected';
        COMMENT ON COLUMN audit_logs.resource_id IS 'UUID of affected resource';
        COMMENT ON COLUMN audit_logs.metadata IS 'Additional context (request_id, changes, etc.)';
    """)

    # Create trigger function to prevent modifications
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit logs are immutable and cannot be modified or deleted';
        END;
        $$ LANGUAGE plpgsql
    """)

    # Create triggers to prevent UPDATE and DELETE
    op.execute("""
        CREATE TRIGGER prevent_audit_log_update
            BEFORE UPDATE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_modification()
    """)

    op.execute("""
        CREATE TRIGGER prevent_audit_log_delete
            BEFORE DELETE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_modification()
    """)

    # Create indexes for audit queries
    op.execute("""
        CREATE INDEX idx_audit_logs_tenant_created
        ON audit_logs(tenant_id, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX idx_audit_logs_user_created
        ON audit_logs(user_id, created_at DESC)
        WHERE user_id IS NOT NULL
    """)

    op.execute("""
        CREATE INDEX idx_audit_logs_action
        ON audit_logs(action, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX idx_audit_logs_resource
        ON audit_logs(resource_type, resource_id, created_at DESC)
    """)

    # Create JSONB GIN index for metadata searches
    op.execute("""
        CREATE INDEX idx_audit_logs_metadata_gin
        ON audit_logs USING gin(metadata)
    """)


def downgrade() -> None:
    """Drop audit_logs table and related functions."""
    op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_delete ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_modification()")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
```

**Migration 6: Create Vector Index**

```python
"""create_vector_indexes

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-10-16 14:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create HNSW index for vector similarity search."""

    # Create HNSW index on embedding_vector
    # Using cosine distance operator for semantic similarity
    # Partial index: only documents with embeddings and not deleted
    op.execute("""
        CREATE INDEX idx_documents_embedding_hnsw
        ON documents
        USING hnsw (embedding_vector vector_cosine_ops)
        WHERE embedding_vector IS NOT NULL AND deleted_at IS NULL
    """)

    # Note: HNSW parameters (m, ef_construction) use defaults
    # m=16: Number of bi-directional links per node
    # ef_construction=64: Size of dynamic candidate list during construction
    # Can be tuned later based on performance testing


def downgrade() -> None:
    """Drop vector indexes."""
    op.execute("DROP INDEX IF EXISTS idx_documents_embedding_hnsw")
```

**Migration 7: Enable Row-Level Security**

```python
"""enable_row_level_security

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2025-10-16 14:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, Sequence[str], None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable Row-Level Security on all tables."""

    # Enable RLS on tenants table
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")

    # Tenants policy: Can only access own tenant record
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON tenants
            FOR ALL
            USING (
                id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
    """)

    # Enable RLS on users table
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")

    # Users policy: Scoped to current tenant
    op.execute("""
        CREATE POLICY user_isolation_policy ON users
            FOR ALL
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
    """)

    # Enable RLS on documents table
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")

    # Documents policy: Scoped to current tenant
    op.execute("""
        CREATE POLICY document_isolation_policy ON documents
            FOR ALL
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
    """)

    # Enable RLS on audit_logs table
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")

    # Audit logs SELECT policy: Scoped to current tenant
    op.execute("""
        CREATE POLICY audit_log_select_policy ON audit_logs
            FOR SELECT
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
    """)

    # Audit logs INSERT policy: Scoped to current tenant
    op.execute("""
        CREATE POLICY audit_log_insert_policy ON audit_logs
            FOR INSERT
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
    """)

    # Note: No UPDATE or DELETE policies for audit_logs (append-only)


def downgrade() -> None:
    """Disable Row-Level Security."""

    # Drop policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON tenants")
    op.execute("DROP POLICY IF EXISTS user_isolation_policy ON users")
    op.execute("DROP POLICY IF EXISTS document_isolation_policy ON documents")
    op.execute("DROP POLICY IF EXISTS audit_log_select_policy ON audit_logs")
    op.execute("DROP POLICY IF EXISTS audit_log_insert_policy ON audit_logs")

    # Disable RLS
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")
```

### SQLAlchemy Models

**Base with Soft Delete Mixin:**

```python
# backend/app/database/base.py (enhanced)

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier (UUID)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated",
    )

    def __repr__(self) -> str:
        """String representation of model instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class SoftDeleteMixin:
    """Mixin for soft delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Soft delete timestamp (NULL = active)",
    )

    @hybrid_property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None

    @is_deleted.expression
    def is_deleted(cls):
        """SQL expression for is_deleted."""
        return cls.deleted_at.isnot(None)

    @hybrid_property
    def is_active(self) -> bool:
        """Check if record is active (not deleted)."""
        return self.deleted_at is None

    @is_active.expression
    def is_active(cls):
        """SQL expression for is_active."""
        return cls.deleted_at.is_(None)

    def soft_delete(self) -> None:
        """Soft delete this record."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.deleted_at = None

    @classmethod
    def active_query(cls):
        """Get base query for active (non-deleted) records."""
        return select(cls).where(cls.deleted_at.is_(None))

    @classmethod
    def deleted_query(cls):
        """Get base query for soft-deleted records."""
        return select(cls).where(cls.deleted_at.isnot(None))
```

**Tenant Model:**

```python
# backend/app/models/tenant.py

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin


class Tenant(Base, SoftDeleteMixin):
    """
    Tenant/Organization model for multi-tenant isolation.

    Represents an organization/customer in the system.
    All tenant-scoped data references this table.
    """

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Organization name",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        comment="Tenant status (active, suspended, trial)",
    )

    kms_key_arn: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="AWS KMS key ARN for tenant-specific encryption",
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="tenant",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="tenant",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, status={self.status})>"
```

**User Model:**

```python
# backend/app/models/user.py

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin


class User(Base, SoftDeleteMixin):
    """
    User model with tenant association.

    Represents a user account within a tenant/organization.
    """

    __tablename__ = "users"

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Tenant this user belongs to",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User email address",
    )

    external_idp_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="External identity provider ID (Cognito sub, Auth0 user_id)",
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User display name",
    )

    role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="User role for RBAC (admin, member, viewer)",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users",
    )

    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="user",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"
```

**Document Model:**

```python
# backend/app/models/document.py

from sqlalchemy import BigInteger, ForeignKey, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database.base import Base, SoftDeleteMixin


class Document(Base, SoftDeleteMixin):
    """
    Document model with S3 storage references and vector embeddings.

    Stores document metadata, S3 location, and semantic embeddings
    for RAG-based search.
    """

    __tablename__ = "documents"

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Tenant this document belongs to",
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who uploaded the document",
    )

    s3_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="S3 object key for document storage",
    )

    s3_bucket: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="S3 bucket name",
    )

    filename: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Original filename from upload",
    )

    content_type: Mapped[str | None] = mapped_column(
        String(127),
        nullable=True,
        comment="MIME type (application/pdf, image/png, etc.)",
    )

    size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="File size in bytes",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="processing",
        comment="Processing status (processing, completed, failed)",
    )

    metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Custom document attributes (JSONB)",
    )

    embedding_vector: Mapped[list[float] | None] = mapped_column(
        Vector(1024),
        nullable=True,
        comment="Vector embedding for semantic search (1024 dimensions)",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="documents",
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="documents",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, tenant_id={self.tenant_id})>"

    @classmethod
    def similarity_search(
        cls,
        embedding: list[float],
        tenant_id: str,
        limit: int = 10,
        threshold: float = 0.7,
    ):
        """
        Create query for vector similarity search within tenant scope.

        Args:
            embedding: Query embedding vector (1024 dimensions)
            tenant_id: Tenant ID to scope search
            limit: Maximum number of results
            threshold: Minimum cosine similarity threshold

        Returns:
            SQLAlchemy select statement with similarity scores
        """
        similarity = func.cosine_distance(cls.embedding_vector, embedding).label("distance")

        return (
            select(cls, similarity)
            .where(cls.tenant_id == tenant_id)
            .where(cls.deleted_at.is_(None))
            .where(cls.embedding_vector.isnot(None))
            .order_by(similarity)
            .limit(limit)
        )
```

**Audit Log Model:**

```python
# backend/app/models/audit_log.py

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AuditLog(Base):
    """
    Immutable audit log model.

    Append-only table for tracking all system operations.
    No updated_at or deleted_at columns - records cannot be modified.
    """

    __tablename__ = "audit_logs"

    # Override to remove updated_at (inherited from Base)
    updated_at: Mapped[None] = None  # type: ignore

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Tenant this audit log belongs to",
    )

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="User who performed action (NULL for system actions)",
    )

    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Action performed (e.g., document.uploaded, user.created)",
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of resource affected",
    )

    resource_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="UUID of affected resource",
    )

    ip_address: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
        comment="Client IP address",
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Browser/client user agent",
    )

    metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Additional context (request_id, changes, etc.)",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="audit_logs",
    )

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="audit_logs",
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, tenant_id={self.tenant_id})>"

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "AuditLog":
        """
        Create audit log entry (append-only).

        This is the only way to create audit logs - enforces immutability.
        """
        audit_log = cls(**kwargs)
        db.add(audit_log)
        await db.flush()
        return audit_log
```

**Models Index:**

```python
# backend/app/models/__init__.py

"""
Database models for the application.

All models use:
- UUID primary keys (String(36))
- Timezone-aware timestamps (TIMESTAMPTZ)
- Soft deletes where applicable
- Tenant isolation via RLS and foreign keys
"""

from app.models.tenant import Tenant
from app.models.user import User
from app.models.document import Document
from app.models.audit_log import AuditLog

__all__ = [
    "Tenant",
    "User",
    "Document",
    "AuditLog",
]
```

### Seed Data

**System Tenant:**

Seed data included in Migration 2 (tenants table creation):

```sql
INSERT INTO tenants (id, name, status, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'System',
    'active',
    NOW(),
    NOW()
);
```

**Purpose:**
- System-level operations (background jobs, maintenance)
- Administrative tasks not scoped to a specific tenant
- Default tenant for system services

**Usage Example:**

```python
SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000000"

# System operation (e.g., cleanup job)
async def cleanup_expired_tokens():
    async with get_session() as db:
        await db.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": SYSTEM_TENANT_ID}
        )
        # Perform system-level operations
```

### Testing Strategy

**Unit Tests for Models:**

```python
# backend/tests/test_models/test_soft_delete.py

import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.models import User, Tenant


@pytest.mark.asyncio
async def test_soft_delete(db_session):
    """Test soft delete functionality."""
    # Create tenant and user
    tenant = Tenant(name="Test Org", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id,
        email="test@example.com",
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    # Verify user is active
    assert user.is_active
    assert not user.is_deleted
    assert user.deleted_at is None

    # Soft delete user
    user.soft_delete()
    await db_session.flush()

    # Verify user is deleted
    assert not user.is_active
    assert user.is_deleted
    assert user.deleted_at is not None
    assert isinstance(user.deleted_at, datetime)

    # Restore user
    user.restore()
    await db_session.flush()

    # Verify user is active again
    assert user.is_active
    assert not user.is_deleted
    assert user.deleted_at is None


@pytest.mark.asyncio
async def test_soft_delete_email_reuse(db_session):
    """Test that emails can be reused after soft deletion."""
    tenant = Tenant(name="Test Org", status="active")
    db_session.add(tenant)
    await db_session.flush()

    # Create user
    user1 = User(
        tenant_id=tenant.id,
        email="reuse@example.com",
        full_name="User 1",
    )
    db_session.add(user1)
    await db_session.flush()

    # Soft delete user
    user1.soft_delete()
    await db_session.commit()

    # Create new user with same email (should succeed)
    user2 = User(
        tenant_id=tenant.id,
        email="reuse@example.com",
        full_name="User 2",
    )
    db_session.add(user2)
    await db_session.commit()

    # Verify both users exist
    result = await db_session.execute(
        select(User).where(User.email == "reuse@example.com")
    )
    users = result.scalars().all()
    assert len(users) == 2
```

**Integration Tests for RLS:**

```python
# backend/tests/test_rls/test_tenant_isolation.py

import pytest
from sqlalchemy import select, text

from app.models import User, Document


@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_access(db_session):
    """Test that RLS prevents cross-tenant data access."""
    # Create two tenants
    tenant1_id = "11111111-1111-1111-1111-111111111111"
    tenant2_id = "22222222-2222-2222-2222-222222222222"

    # Create users in different tenants
    user1 = User(
        tenant_id=tenant1_id,
        email="user1@tenant1.com",
        full_name="User 1",
    )
    user2 = User(
        tenant_id=tenant2_id,
        email="user2@tenant2.com",
        full_name="User 2",
    )
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Set tenant context to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # Query should only return tenant1's user
    result = await db_session.execute(select(User))
    users = result.scalars().all()

    assert len(users) == 1
    assert users[0].tenant_id == tenant1_id
    assert users[0].email == "user1@tenant1.com"


@pytest.mark.asyncio
async def test_rls_prevents_unauthorized_insert(db_session):
    """Test that RLS prevents inserting data for another tenant."""
    tenant1_id = "11111111-1111-1111-1111-111111111111"
    tenant2_id = "22222222-2222-2222-2222-222222222222"

    # Set tenant context to tenant1
    await db_session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant1_id}
    )

    # Try to insert user for tenant2 (should fail or be blocked)
    user = User(
        tenant_id=tenant2_id,
        email="user@tenant2.com",
        full_name="Unauthorized User",
    )
    db_session.add(user)

    with pytest.raises(Exception):  # RLS policy violation
        await db_session.commit()
```

**Fuzz Tests for Tenant Isolation:**

```python
# backend/tests/test_fuzz/test_tenant_leakage.py

import pytest
import uuid
from sqlalchemy import select, text

from app.models import Document


@pytest.mark.asyncio
async def test_fuzz_tenant_isolation(db_session):
    """Fuzz test to detect tenant data leakage."""
    # Create 10 tenants with 5 documents each
    tenant_ids = [str(uuid.uuid4()) for _ in range(10)]

    for tenant_id in tenant_ids:
        for i in range(5):
            doc = Document(
                tenant_id=tenant_id,
                user_id=str(uuid.uuid4()),
                s3_key=f"test/{tenant_id}/{i}.pdf",
                s3_bucket="test-bucket",
                filename=f"document_{i}.pdf",
                status="completed",
            )
            db_session.add(doc)

    await db_session.commit()

    # Test each tenant in isolation
    for tenant_id in tenant_ids:
        await db_session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )

        result = await db_session.execute(select(Document))
        docs = result.scalars().all()

        # Should only see own documents
        assert len(docs) == 5
        for doc in docs:
            assert doc.tenant_id == tenant_id
            assert doc.s3_key.startswith(f"test/{tenant_id}/")


@pytest.mark.asyncio
async def test_audit_log_immutability(db_session):
    """Test that audit logs cannot be modified or deleted."""
    from app.models import AuditLog

    tenant_id = str(uuid.uuid4())

    # Create audit log
    audit_log = await AuditLog.create(
        db=db_session,
        tenant_id=tenant_id,
        action="document.uploaded",
        resource_type="document",
        resource_id=str(uuid.uuid4()),
        metadata={"filename": "test.pdf"},
    )
    await db_session.commit()

    # Try to update (should fail)
    audit_log.action = "document.deleted"
    with pytest.raises(Exception):  # Trigger should prevent UPDATE
        await db_session.commit()

    # Try to delete (should fail)
    await db_session.rollback()
    db_session.delete(audit_log)
    with pytest.raises(Exception):  # Trigger should prevent DELETE
        await db_session.commit()
```

### Security Considerations

**Defense-in-Depth Checklist:**

Database Level:
- [x] Row-Level Security (RLS) enabled on all tables
- [x] RLS policies enforce tenant_id filtering
- [x] Minimal permissions for application database role
- [x] Triggers prevent UPDATE/DELETE on audit_logs
- [x] Soft deletes with deleted_at column
- [x] Partial unique indexes for soft-deleted records
- [x] Foreign keys use ON DELETE RESTRICT

Application Level:
- [x] Tenant context extracted from JWT claims
- [x] Tenant context validated and set in middleware
- [x] All queries include tenant_id filtering (defense-in-depth)
- [x] Audit logging for all CRUD operations
- [x] No raw SQL without tenant filtering

Testing Level:
- [x] Unit tests for RLS policies
- [x] Integration tests for tenant isolation
- [x] Fuzz tests to detect cross-tenant leaks
- [x] Tests verify UPDATE/DELETE fails on audit_logs

Operational Level:
- [ ] Monitor audit logs for suspicious patterns
- [ ] Alerts for cross-tenant access attempts
- [ ] Regular RLS policy audits
- [ ] Periodic integrity checks on audit log hash chains (if implemented)

**HIPAA Compliance Points:**

- Timezone-aware timestamps (TIMESTAMPTZ) on all tables
- Audit logging of all data access and modifications
- Soft deletes preserve data for retention requirements
- Immutable audit logs prevent tampering
- Per-tenant encryption key support (kms_key_arn column)
- RLS provides access control at database level
- Foreign keys maintain referential integrity

### Performance Considerations

**Indexing Strategy:**

1. **Composite Indexes:** Always list tenant_id first for partition pruning
2. **Partial Indexes:** Use WHERE deleted_at IS NULL for active records only
3. **HNSW Indexes:** Approximate nearest neighbor search with sub-second latency
4. **JSONB GIN Indexes:** Enable flexible metadata queries without schema changes

**Query Optimization:**

```python
# Good: Index-optimized tenant-scoped query
stmt = select(Document).where(
    Document.tenant_id == tenant_id,
    Document.deleted_at.is_(None),
).order_by(Document.created_at.desc()).limit(10)

# Bad: Missing tenant_id filter (full table scan)
stmt = select(Document).order_by(Document.created_at.desc()).limit(10)
```

**Partitioning Recommendations:**

For massive scale (millions of documents per tenant):

```sql
-- Partition by tenant_id for better isolation and performance
CREATE TABLE documents_partitioned (
    -- same columns as documents
) PARTITION BY HASH (tenant_id);

-- Create partitions
CREATE TABLE documents_partition_0 PARTITION OF documents_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE documents_partition_1 PARTITION OF documents_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);

-- etc.
```

For time-series data (audit logs):

```sql
-- Partition by created_at for time-based queries
CREATE TABLE audit_logs_partitioned (
    -- same columns as audit_logs
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE audit_logs_2025_10 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE audit_logs_2025_11 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- etc.
```

**Monitoring Queries:**

```sql
-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check unused indexes (candidates for removal)
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND schemaname = 'public';
```

### Railway Configuration

**PostgreSQL Provisioning with pgvector:**

Railway provides a specialized PostgreSQL template with pgvector pre-installed:

**Deployment Options:**

1. **Using Railway pgvector Template** (Recommended):
   - Deploy URL: https://railway.com/deploy/3jJFCA
   - Based on Docker image: `pgvector/pgvector:pg15`
   - pgvector extension pre-installed and ready to enable
   - Superuser access available (Railway uses Docker's official postgres image)

2. **Manual Extension Enablement** (if using standard PostgreSQL template):
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   Note: This requires pgvector to be available in the PostgreSQL installation.

**Railway Environment Variables Provided:**

Railway automatically provides these environment variables for PostgreSQL:

```bash
# Railway-provided PostgreSQL variables
PGHOST=<hostname>
PGPORT=5432
PGUSER=postgres
PGPASSWORD=<generated-password>
PGDATABASE=railway
DATABASE_URL=postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE

# Application-specific variables (must be set manually)
ENVIRONMENT=production
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://app.example.com
OIDC_ISSUER_URL=https://your-idp.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
```

**Connection Pooling Configuration:**

Already configured in `/Users/mattfili/Dev/hippa-compliant-railway-stack/backend/app/database/engine.py`:

```python
engine = create_async_engine(
    database_url,
    pool_size=10,        # 10 persistent connections
    max_overflow=10,     # 10 additional connections when pool full
    pool_timeout=30,     # 30s timeout for connection acquisition
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
)
```

**Connection Limit Considerations:**

Railway PostgreSQL connection limits vary by plan. The application is configured for 20 total connections (pool_size=10 + max_overflow=10), which fits within most Railway plans. Monitor usage and adjust based on your plan tier:

- Free/Hobby tier: ~20-50 connections
- Pro tier: 100+ connections
- Verify your plan's connection limit in Railway dashboard

**PostgreSQL Configuration Tuning:**

Use `ALTER SYSTEM` for configuration changes (requires restart):

```sql
-- Optimize for production workload (8GB RAM example)
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET max_connections = '100';

-- Optimize for HIPAA audit logging (WAL retention)
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET archive_mode = 'on';
```

Then restart the PostgreSQL service in Railway dashboard.

**Backup Configuration:**

Enable Railway's native "Backups" feature for HIPAA compliance:

1. Navigate to PostgreSQL service in Railway dashboard
2. Enable "Backups" feature
3. Configure retention period (recommend 30+ days for HIPAA)
4. Verify backup schedule and test restoration

**Template Metadata (template.json):**

Create `template.json` for Railway template publishing:

```json
{
  "name": "HIPAA-Compliant RAG Template",
  "description": "Production-ready multi-tenant RAG application with HIPAA compliance, pgvector embeddings, and audit logging",
  "repository": "https://github.com/your-org/hipaa-compliant-railway-stack",
  "keywords": [
    "hipaa",
    "rag",
    "pgvector",
    "multi-tenant",
    "fastapi",
    "postgresql",
    "claude",
    "bedrock",
    "healthcare"
  ],
  "services": [
    {
      "name": "postgres",
      "source": {
        "image": "pgvector/pgvector:pg15"
      },
      "config": {
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD}",
        "POSTGRES_DB": "railway"
      }
    },
    {
      "name": "backend",
      "source": {
        "repo": "https://github.com/your-org/hipaa-compliant-railway-stack",
        "directory": "backend"
      },
      "config": {
        "DATABASE_URL": "${{postgres.DATABASE_URL}}",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "INFO",
        "ALLOWED_ORIGINS": "${ALLOWED_ORIGINS}",
        "OIDC_ISSUER_URL": "${OIDC_ISSUER_URL}",
        "OIDC_CLIENT_ID": "${OIDC_CLIENT_ID}",
        "OIDC_CLIENT_SECRET": "${OIDC_CLIENT_SECRET}",
        "AWS_REGION": "${AWS_REGION}",
        "AWS_ACCESS_KEY_ID": "${AWS_ACCESS_KEY_ID}",
        "AWS_SECRET_ACCESS_KEY": "${AWS_SECRET_ACCESS_KEY}"
      },
      "healthcheck": {
        "path": "/api/v1/health/ready",
        "timeout": 30
      }
    }
  ],
  "variables": [
    {
      "name": "POSTGRES_PASSWORD",
      "description": "PostgreSQL password (auto-generated)",
      "default": "${RANDOM_PASSWORD}"
    },
    {
      "name": "ALLOWED_ORIGINS",
      "description": "Comma-separated list of allowed CORS origins (e.g., https://app.example.com,https://admin.example.com)",
      "required": true
    },
    {
      "name": "OIDC_ISSUER_URL",
      "description": "OpenID Connect issuer URL for authentication (e.g., https://cognito.amazonaws.com/us-east-1_XXXXXXXXX)",
      "required": true
    },
    {
      "name": "OIDC_CLIENT_ID",
      "description": "OpenID Connect client ID",
      "required": true
    },
    {
      "name": "OIDC_CLIENT_SECRET",
      "description": "OpenID Connect client secret",
      "required": true,
      "sensitive": true
    },
    {
      "name": "AWS_REGION",
      "description": "AWS region for Bedrock and KMS services (e.g., us-east-1)",
      "required": true,
      "default": "us-east-1"
    },
    {
      "name": "AWS_ACCESS_KEY_ID",
      "description": "AWS access key ID for Bedrock and KMS",
      "required": true,
      "sensitive": true
    },
    {
      "name": "AWS_SECRET_ACCESS_KEY",
      "description": "AWS secret access key for Bedrock and KMS",
      "required": true,
      "sensitive": true
    }
  ],
  "instructions": "# HIPAA-Compliant RAG Template\n\n## Prerequisites\n\n1. **AWS Account** with:\n   - Amazon Bedrock enabled (Claude for LLM, Titan for embeddings)\n   - KMS for encryption\n   - S3 bucket for document storage\n\n2. **OpenID Connect Provider** (AWS Cognito, Auth0, Okta, etc.) with:\n   - OIDC/SAML authentication configured\n   - Custom claim `custom:tenant_id` for multi-tenancy\n\n3. **Railway Account** with:\n   - Pro plan (for production workloads)\n   - Business Associate Agreement (BAA) signed for HIPAA compliance\n\n## Setup Instructions\n\n1. **Deploy this template** - Railway will provision PostgreSQL and backend services\n\n2. **Configure environment variables** in Railway dashboard:\n   - Set all required variables (OIDC, AWS credentials, CORS origins)\n\n3. **Verify pgvector extension**:\n   - Open Railway PostgreSQL console\n   - Run: `SELECT * FROM pg_available_extensions WHERE name = 'vector';`\n   - If not installed, contact Railway support\n\n4. **Database migrations run automatically** on first deployment via `startup.sh`\n\n5. **Verify health checks**:\n   - Wait for deployment to complete\n   - Check: `https://<your-backend-url>/api/v1/health/ready`\n\n6. **Create your first tenant**:\n   - Use API or database console to insert tenant record\n   - System tenant (ID: `00000000-0000-0000-0000-000000000000`) is auto-created\n\n## HIPAA Compliance Notes\n\n- **BAA Required**: Ensure Railway BAA is signed before storing PHI\n- **Encryption**: Enable encryption at rest in Railway PostgreSQL settings\n- **Audit Logs**: Immutable audit logs are enabled by default\n- **Access Controls**: RLS policies enforce tenant isolation at database level\n- **Backups**: Enable Railway backups with 30+ day retention\n\n## Support\n\nFor issues or questions, see the [GitHub repository](https://github.com/your-org/hipaa-compliant-railway-stack) or Railway community forums."
}

### Extension Points

**Feature 4: Per-Tenant Encryption**

```python
# kms_key_arn column already exists in tenants table
tenant = await db.get(Tenant, tenant_id)
kms_key_arn = tenant.kms_key_arn

# Use KMS key for encrypting sensitive document fields
encrypted_data = await kms_client.encrypt(
    KeyId=kms_key_arn,
    Plaintext=document_content,
)
```

**Feature 5: Document Ingestion**

```python
# Documents table already supports S3 metadata
document = Document(
    tenant_id=tenant_id,
    user_id=user_id,
    s3_key=f"documents/{tenant_id}/{doc_id}.pdf",
    s3_bucket="app-documents-prod",
    filename="report.pdf",
    content_type="application/pdf",
    size_bytes=1024000,
    status="processing",
)
```

**Feature 7: Embedding Generation**

```python
# embedding_vector column already exists in documents table
document.embedding_vector = await generate_embedding(document_text)
document.status = "completed"
await db.commit()
```

**Feature 8: Vector Search**

```python
# Use Document.similarity_search() helper
query_embedding = await generate_embedding(query_text)

results = await db.execute(
    Document.similarity_search(
        embedding=query_embedding,
        tenant_id=tenant_id,
        limit=10,
        threshold=0.7,
    )
)

for doc, distance in results:
    print(f"{doc.filename}: similarity={1 - distance}")
```

**Feature 10: Audit Logging**

```python
# AuditLog table already supports all required fields
await AuditLog.create(
    db=db,
    tenant_id=tenant_id,
    user_id=user_id,
    action="document.uploaded",
    resource_type="document",
    resource_id=document.id,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    metadata={
        "filename": document.filename,
        "size_bytes": document.size_bytes,
        "request_id": request.state.request_id,
    },
)
```

**Feature 13: RBAC**

```python
# role column already exists in users table
user = await db.get(User, user_id)

if user.role == "admin":
    # Allow administrative operations
    pass
elif user.role == "member":
    # Allow standard operations
    pass
elif user.role == "viewer":
    # Read-only access
    pass
```

## Out of Scope

**Not Included in Feature 2:**

- RBAC tables (roles, permissions, role_assignments) - Feature 13
- Encryption key management tables - Feature 4
- Document chunks table (separate from documents) - Future feature
- PHI detection/scrubbing logic - Feature 14
- Anomaly detection tables - Feature 16
- User sessions table (JWT tokens are stateless)
- Notification preferences table
- Webhook configuration table
- API rate limiting tables

**Future Enhancements:**

- Hash chain implementation in audit_logs (previous_hash, chain_hash columns)
- Table partitioning for massive scale (tenant_id or created_at)
- Read replicas for query performance
- Separate audit log export to immutable external storage
- Multi-level tenancy (parent_tenant_id in tenants table)
- Tenant quotas (max_users, max_storage_gb columns)

## Success Criteria

**Functional Success:**
- All 7 migrations run successfully without errors
- All 4 tables created with correct schema and constraints
- System tenant seed data inserted
- RLS policies prevent cross-tenant access in tests
- Soft deletes work correctly with partial unique indexes
- Audit log UPDATE/DELETE operations fail as expected
- Vector similarity search returns relevant results

**Non-Functional Success:**
- Tenant-scoped queries use composite indexes (EXPLAIN ANALYZE)
- Vector search completes in <100ms for 10k documents
- Audit log writes do not block application transactions
- Database connection pooling maintains stable performance under load
- RLS policies add <5ms overhead to queries
- All indexes fit in available PostgreSQL RAM (pg_stat_user_indexes)

**Security Success:**
- Fuzz tests detect zero cross-tenant data leaks
- RLS policies block unauthorized access attempts
- Audit log immutability enforced at database level
- Foreign key constraints prevent orphaned records
- Soft deletes preserve data for compliance requirements

**Developer Experience Success:**
- SQLAlchemy models clearly document all columns and relationships
- Mixins (SoftDeleteMixin) reduce code duplication
- Helper methods (similarity_search, soft_delete) simplify common operations
- Migration files are well-commented and reversible
- Test fixtures provide easy setup for integration tests
