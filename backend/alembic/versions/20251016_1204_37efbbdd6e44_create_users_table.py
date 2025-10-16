"""create_users_table

Revision ID: 37efbbdd6e44
Revises: dd4cd840bc88
Create Date: 2025-10-16 12:04:07.990218

Creates the users table with tenant association:
- Foreign key to tenants table with ON DELETE RESTRICT
- Soft delete support (deleted_at column)
- Partial unique index for (tenant_id, email) to allow email reuse after deletion
- Indexes for efficient tenant-scoped queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37efbbdd6e44'
down_revision: Union[str, Sequence[str], None] = 'dd4cd840bc88'
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
    """)
    op.execute("""
        COMMENT ON COLUMN users.external_idp_id IS 'External identity provider ID (Cognito sub, Auth0 user_id)';
    """)
    op.execute("""
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
