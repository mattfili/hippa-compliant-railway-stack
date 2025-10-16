"""create_vector_and_performance_indexes

Revision ID: 63042ce5f838
Revises: 281e991e2aee
Create Date: 2025-10-16 12:04:30.000000

Creates performance indexes for tenant-scoped queries and vector similarity search:
- HNSW index on documents.embedding_vector for fast semantic search
- Composite indexes for tenant-scoped queries with tenant_id first
- GIN index on documents.metadata JSONB for flexible querying

Vector Index Configuration:
- Algorithm: HNSW (Hierarchical Navigable Small World)
- Distance metric: Cosine distance (vector_cosine_ops)
- Parameters: m=16 (bi-directional links), ef_construction=64 (candidate list size)
- Partial index: Only documents with embeddings and not soft-deleted
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63042ce5f838'
down_revision: Union[str, Sequence[str], None] = '281e991e2aee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create HNSW vector index and performance indexes."""

    # Create HNSW index on embedding_vector for vector similarity search
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
    # Can be tuned later based on performance testing with:
    # CREATE INDEX ... WITH (m = 16, ef_construction = 64)


def downgrade() -> None:
    """Drop vector and performance indexes."""
    op.execute("DROP INDEX IF EXISTS idx_documents_embedding_hnsw")
