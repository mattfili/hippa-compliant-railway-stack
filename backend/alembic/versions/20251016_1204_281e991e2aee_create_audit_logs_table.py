"""create_audit_logs_table

Revision ID: 281e991e2aee
Revises: e2495309c71b
Create Date: 2025-10-16 12:04:24.150482

Creates the audit_logs table with immutability enforcement:
- Foreign keys to tenants and users with ON DELETE RESTRICT
- No updated_at or deleted_at columns (append-only)
- Database triggers to prevent UPDATE and DELETE operations
- INET type for IP addresses
- JSONB metadata field for flexible audit context
- Indexes for efficient audit queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '281e991e2aee'
down_revision: Union[str, Sequence[str], None] = 'e2495309c71b'
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
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.action IS 'Action performed (e.g., document.uploaded, user.created)';
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.resource_type IS 'Type of resource affected';
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.resource_id IS 'UUID of affected resource';
    """)
    op.execute("""
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
