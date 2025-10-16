"""enable_row_level_security

Revision ID: f6g7h8i9j0k1
Revises: 63042ce5f838
Create Date: 2025-10-16 12:05:00.000000

Enables Row-Level Security (RLS) on all tables with tenant isolation policies:

Tenants Table:
- Policy allows access only to own tenant record via app.current_tenant_id

Users Table:
- Policy filters users by tenant_id = app.current_tenant_id

Documents Table:
- Policy filters documents by tenant_id = app.current_tenant_id

Audit Logs Table:
- Separate SELECT and INSERT policies for tenant-scoped access
- No UPDATE/DELETE policies (append-only enforcement at trigger level)

Usage Pattern:
    -- Set tenant context before queries
    SET LOCAL app.current_tenant_id = '<tenant-uuid>';

    -- All subsequent queries automatically filtered by RLS
    SELECT * FROM users;  -- Returns only users for current tenant

Notes:
- Uses NULLIF to handle missing app.current_tenant_id gracefully
- RLS provides defense-in-depth alongside application-layer filtering
- System/admin operations may need to bypass RLS via role switching
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, Sequence[str], None] = '63042ce5f838'
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
    # Database triggers prevent UPDATE/DELETE operations


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
