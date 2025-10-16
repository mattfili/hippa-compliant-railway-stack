"""
Audit log model for immutable audit trail.

This module provides the AuditLog model which is append-only:
- No updated_at column (records cannot be updated)
- No deleted_at column (records cannot be deleted)
- Database triggers prevent UPDATE and DELETE operations
- Only INSERT operations are allowed via create() classmethod
"""

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AuditLog(Base):
    """
    Immutable audit log model.

    Append-only table for tracking all system operations.
    No updated_at or deleted_at columns - records cannot be modified.
    Database triggers enforce immutability at the database level.

    Attributes:
        tenant_id: Foreign key to tenants table
        user_id: Foreign key to users table (nullable for system actions)
        action: Action performed (e.g., document.uploaded, user.created)
        resource_type: Type of resource affected
        resource_id: UUID of affected resource
        ip_address: Client IP address (stored as string for cross-DB compatibility)
        user_agent: Browser/client user agent
        audit_metadata: Additional context (request_id, changes, etc.)
                       (Python attr name; database column is 'metadata')
        tenant: Relationship to Tenant model
        user: Relationship to User model
    """

    __tablename__ = "audit_logs"

    # Don't include updated_at column in audit_logs (it's immutable)
    __mapper_args__ = {
        "exclude_properties": ["updated_at"]
    }

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
        String(45),  # IPv6 max length
        nullable=True,
        comment="Client IP address",
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Browser/client user agent",
    )

    # Use 'audit_metadata' as Python attribute name to avoid conflict with SQLAlchemy's 'metadata'
    # Database column name is still 'metadata'
    # Use JSON with JSONB variant for PostgreSQL compatibility
    audit_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
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
        """String representation of audit log."""
        return f"<AuditLog(id={self.id}, action={self.action}, tenant_id={self.tenant_id})>"

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "AuditLog":
        """
        Create audit log entry (append-only).

        This is the only way to create audit logs - enforces immutability.
        No update() or delete() methods are exposed.

        Args:
            db: Database session
            **kwargs: Audit log fields (tenant_id, action, resource_type, etc.)
                     Use 'audit_metadata' parameter (not 'metadata') to set metadata field.

        Returns:
            AuditLog: Created audit log instance

        Example:
            audit_log = await AuditLog.create(
                db=db,
                tenant_id="123e4567-e89b-12d3-a456-426614174000",
                action="document.uploaded",
                resource_type="document",
                resource_id="456e789a-b12c-34d5-e678-9abcdef01234",
                audit_metadata={"filename": "test.pdf"}
            )
        """
        audit_log = cls(**kwargs)
        db.add(audit_log)
        await db.flush()
        return audit_log
