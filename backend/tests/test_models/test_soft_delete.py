"""
Tests for soft delete functionality in SoftDeleteMixin.

This module tests the soft delete mixin which provides:
- soft_delete() method to set deleted_at timestamp
- restore() method to clear deleted_at timestamp
- is_deleted hybrid property for checking deletion status
- is_active hybrid property for checking active status
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, SoftDeleteMixin


# Create a test model for testing soft delete functionality
class TestModel(Base, SoftDeleteMixin):
    """Test model for soft delete functionality."""

    __tablename__ = "test_soft_delete_model"

    name: Mapped[str] = mapped_column(String(255), nullable=False)


@pytest.mark.asyncio
async def test_soft_delete_sets_timestamp(db_session):
    """Test that soft_delete() sets deleted_at timestamp."""
    # Create a test record
    record = TestModel(name="Test Record")
    db_session.add(record)
    await db_session.flush()

    # Verify record is active initially
    assert record.deleted_at is None

    # Perform soft delete
    record.soft_delete()
    await db_session.flush()

    # Verify deleted_at is set
    assert record.deleted_at is not None
    assert isinstance(record.deleted_at, datetime)
    # Verify timestamp is recent (within last 5 seconds)
    time_diff = datetime.now(timezone.utc) - record.deleted_at
    assert time_diff.total_seconds() < 5


@pytest.mark.asyncio
async def test_restore_clears_timestamp(db_session):
    """Test that restore() clears deleted_at timestamp."""
    # Create and soft delete a test record
    record = TestModel(name="Test Record")
    db_session.add(record)
    await db_session.flush()

    record.soft_delete()
    await db_session.flush()

    # Verify record is deleted
    assert record.deleted_at is not None

    # Restore the record
    record.restore()
    await db_session.flush()

    # Verify deleted_at is cleared
    assert record.deleted_at is None


@pytest.mark.asyncio
async def test_is_deleted_property(db_session):
    """Test that is_deleted property returns correct boolean."""
    # Create a test record
    record = TestModel(name="Test Record")
    db_session.add(record)
    await db_session.flush()

    # Verify is_deleted is False for active record
    assert record.is_deleted is False

    # Soft delete the record
    record.soft_delete()
    await db_session.flush()

    # Verify is_deleted is True
    assert record.is_deleted is True

    # Test SQL expression in query
    result = await db_session.execute(
        select(TestModel).where(TestModel.is_deleted == True)
    )
    deleted_records = result.scalars().all()
    assert len(deleted_records) == 1
    assert deleted_records[0].id == record.id


@pytest.mark.asyncio
async def test_is_active_property(db_session):
    """Test that is_active property returns correct boolean."""
    # Create a test record
    record = TestModel(name="Test Record")
    db_session.add(record)
    await db_session.flush()

    # Verify is_active is True for active record
    assert record.is_active is True

    # Soft delete the record
    record.soft_delete()
    await db_session.flush()

    # Verify is_active is False
    assert record.is_active is False

    # Test SQL expression in query
    result = await db_session.execute(
        select(TestModel).where(TestModel.is_active == True)
    )
    active_records = result.scalars().all()
    assert len(active_records) == 0

    # Restore and verify is_active is True again
    record.restore()
    await db_session.flush()

    result = await db_session.execute(
        select(TestModel).where(TestModel.is_active == True)
    )
    active_records = result.scalars().all()
    assert len(active_records) == 1
    assert active_records[0].id == record.id
