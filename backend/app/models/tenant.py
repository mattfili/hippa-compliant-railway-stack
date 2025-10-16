"""
Tenant model for multi-tenant isolation.

This module provides the Tenant model which represents organizations/customers
in the multi-tenant system. All tenant-scoped data references this table.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin


class Tenant(Base, SoftDeleteMixin):
    """
    Tenant/Organization model for multi-tenant isolation.

    Represents an organization/customer in the system.
    All tenant-scoped data references this table.

    Attributes:
        name: Organization name
        status: Tenant status (active, suspended, trial)
        kms_key_arn: AWS KMS key ARN for tenant-specific encryption
        users: Relationship to User model
        documents: Relationship to Document model
        audit_logs: Relationship to AuditLog model
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
        """String representation of Tenant instance."""
        return f"<Tenant(id={self.id}, name={self.name}, status={self.status})>"
