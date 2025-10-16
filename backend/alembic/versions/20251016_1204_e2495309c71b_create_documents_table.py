"""create_documents_table

Revision ID: e2495309c71b
Revises: 37efbbdd6e44
Create Date: 2025-10-16 12:04:13.350071

Creates the documents table with pgvector support:
- Foreign keys to tenants and users with ON DELETE RESTRICT
- Soft delete support (deleted_at column)
- Vector column for embeddings (VECTOR(1024), nullable)
- JSONB metadata field for flexible attributes
- Check constraint for status enum
- Indexes for efficient tenant-scoped queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2495309c71b'
down_revision: Union[str, Sequence[str], None] = '37efbbdd6e44'
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
    """)
    op.execute("""
        COMMENT ON COLUMN documents.s3_key IS 'S3 object key for document storage';
    """)
    op.execute("""
        COMMENT ON COLUMN documents.status IS 'Processing status (processing, completed, failed)';
    """)
    op.execute("""
        COMMENT ON COLUMN documents.metadata IS 'Custom document attributes (JSONB)';
    """)
    op.execute("""
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
