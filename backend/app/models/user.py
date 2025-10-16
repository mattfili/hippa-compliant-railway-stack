"""
User model with tenant association.

This module provides the User model which represents user accounts within
a tenant/organization.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin


class User(Base, SoftDeleteMixin):
    """
    User model with tenant association.

    Represents a user account within a tenant/organization.

    Attributes:
        tenant_id: Foreign key to tenants table
        email: User email address
        external_idp_id: External identity provider ID (Cognito sub, Auth0 user_id)
        full_name: Display name
        role: User role for RBAC (admin, member, viewer)
        last_login_at: Last successful login timestamp
        tenant: Relationship to Tenant model
        documents: Relationship to Document model
        audit_logs: Relationship to AuditLog model
    """

    __tablename__ = "users"

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Tenant this user belongs to",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User email address",
    )

    external_idp_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="External identity provider ID (Cognito sub, Auth0 user_id)",
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User display name",
    )

    role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="User role for RBAC (admin, member, viewer)",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users",
    )

    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="user",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """String representation of User instance."""
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"
