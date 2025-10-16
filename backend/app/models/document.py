"""
Document model with S3 storage references and vector embeddings.

This module provides the Document model which stores document metadata,
S3 location, and semantic embeddings for RAG-based search.
"""

from sqlalchemy import BigInteger, ForeignKey, JSON, String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database.base import Base, SoftDeleteMixin


class Document(Base, SoftDeleteMixin):
    """
    Document model with S3 storage references and vector embeddings.

    Stores document metadata, S3 location, and semantic embeddings
    for RAG-based search.

    Attributes:
        tenant_id: Foreign key to tenants table
        user_id: Foreign key to users table (uploader)
        s3_key: S3 object key for document storage
        s3_bucket: S3 bucket name
        filename: Original filename from upload
        content_type: MIME type (application/pdf, image/png, etc.)
        size_bytes: File size in bytes
        status: Processing status (processing, completed, failed)
        doc_metadata: JSONB for flexible custom attributes
                     (Python attr name; database column is 'metadata')
        embedding_vector: Vector embedding for semantic search (1024 dimensions)
        tenant: Relationship to Tenant model
        user: Relationship to User model
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

    # Use 'doc_metadata' as Python attribute name to avoid conflict with SQLAlchemy's 'metadata'
    # Database column name is still 'metadata'
    # Use JSON with JSONB variant for PostgreSQL compatibility
    doc_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
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
        """String representation of Document instance."""
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
        # Calculate cosine distance (lower is more similar)
        # Note: pgvector's cosine_distance returns 0 for identical vectors, 2 for opposite
        similarity = func.cosine_distance(cls.embedding_vector, embedding).label("distance")

        return (
            select(cls, similarity)
            .where(cls.tenant_id == tenant_id)
            .where(cls.deleted_at.is_(None))
            .where(cls.embedding_vector.isnot(None))
            .order_by(similarity)
            .limit(limit)
        )
