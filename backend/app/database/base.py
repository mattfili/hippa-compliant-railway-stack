"""
SQLAlchemy declarative base model with common fields.

This module provides the base class for all database models with:
- UUID primary key
- Automatic created_at timestamp
- Automatic updated_at timestamp
- Optional soft delete support via SoftDeleteMixin
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Base class for all database models.

    Provides common fields that should be present on all tables:
    - id: UUID primary key
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last updated
    """

    # Don't create a table for the base class
    __abstract__ = True

    # Common fields for all models
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier (UUID)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated",
    )

    def __repr__(self) -> str:
        """String representation of model instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns:
            dict: Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class SoftDeleteMixin:
    """
    Mixin for soft delete support.

    Provides soft delete functionality with:
    - deleted_at timestamp column
    - is_deleted hybrid property (works in Python and SQL)
    - is_active hybrid property (works in Python and SQL)
    - soft_delete() method to mark as deleted
    - restore() method to undelete
    - active_query() classmethod for querying active records
    - deleted_query() classmethod for querying deleted records
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Soft delete timestamp (NULL = active)",
    )

    @hybrid_property
    def is_deleted(self) -> bool:
        """
        Check if record is soft deleted.

        Returns:
            bool: True if record is deleted, False otherwise
        """
        return self.deleted_at is not None

    @is_deleted.expression
    def is_deleted(cls):
        """
        SQL expression for is_deleted.

        Returns:
            SQLAlchemy expression for use in WHERE clauses
        """
        return cls.deleted_at.isnot(None)

    @hybrid_property
    def is_active(self) -> bool:
        """
        Check if record is active (not deleted).

        Returns:
            bool: True if record is active, False if deleted
        """
        return self.deleted_at is None

    @is_active.expression
    def is_active(cls):
        """
        SQL expression for is_active.

        Returns:
            SQLAlchemy expression for use in WHERE clauses
        """
        return cls.deleted_at.is_(None)

    def soft_delete(self) -> None:
        """
        Soft delete this record.

        Sets deleted_at timestamp to current UTC time.
        """
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """
        Restore soft-deleted record.

        Clears the deleted_at timestamp.
        """
        self.deleted_at = None

    @classmethod
    def active_query(cls):
        """
        Get base query for active (non-deleted) records.

        Returns:
            SQLAlchemy select statement filtering for active records
        """
        return select(cls).where(cls.deleted_at.is_(None))

    @classmethod
    def deleted_query(cls):
        """
        Get base query for soft-deleted records.

        Returns:
            SQLAlchemy select statement filtering for deleted records
        """
        return select(cls).where(cls.deleted_at.isnot(None))
