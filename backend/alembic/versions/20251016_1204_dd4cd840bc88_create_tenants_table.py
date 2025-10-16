"""create_tenants_table

Revision ID: dd4cd840bc88
Revises: 1ef269d5fac7
Create Date: 2025-10-16 12:04:03.308127

Creates the tenants table for multi-tenant organization data with:
- Soft delete support (deleted_at column)
- System tenant seed data
- Indexes for efficient querying
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd4cd840bc88'
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
    """)
    op.execute("""
        COMMENT ON COLUMN tenants.name IS 'Organization name';
    """)
    op.execute("""
        COMMENT ON COLUMN tenants.status IS 'Tenant status (active, suspended, trial)';
    """)
    op.execute("""
        COMMENT ON COLUMN tenants.kms_key_arn IS 'AWS KMS key ARN for tenant-specific encryption';
    """)
    op.execute("""
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
