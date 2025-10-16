"""enable_pgvector_extension

Revision ID: 1ef269d5fac7
Revises:
Create Date: 2025-10-15 15:06:12.132972

This initial migration enables the pgvector extension in PostgreSQL,
which is required for vector similarity search operations.

Future migrations will add the following tables:
- tenant: Multi-tenant organization data
- user: User accounts with tenant association
- document: Document metadata and storage references
- document_embedding: Vector embeddings for RAG search

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '1ef269d5fac7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enable pgvector extension.

    The pgvector extension adds support for vector data types and operations,
    which are essential for storing and querying document embeddings in RAG applications.
    """
    # Enable pgvector extension (idempotent operation)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Verify extension is available
    connection = op.get_bind()
    result = connection.execute(
        text("SELECT * FROM pg_available_extensions WHERE name = 'vector'")
    ).fetchone()

    if not result:
        raise Exception(
            "pgvector extension not available in this PostgreSQL installation. "
            "Please ensure Railway PostgreSQL uses pgvector/pgvector:pg15 image. "
            "Deploy using Railway pgvector template: https://railway.com/deploy/3jJFCA"
        )


def downgrade() -> None:
    """
    Disable pgvector extension.

    Note: This will fail if any tables are using vector types.
    Ensure all tables using vector types are dropped before running this downgrade.
    """
    # Drop pgvector extension (idempotent operation)
    op.execute("DROP EXTENSION IF EXISTS vector;")
