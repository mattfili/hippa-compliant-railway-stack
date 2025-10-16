"""
SQLAlchemy async engine setup with connection pooling and retry logic.

This module provides an async database engine factory with:
- Connection pooling configuration (pool_size=10, max_overflow=10)
- Connection retry logic with exponential backoff
- Database URL validation
- Async session factory with proper lifecycle management
"""

import asyncio
import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

# Global engine instance
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    """
    Get and validate DATABASE_URL from environment.
    
    Returns:
        str: Validated database URL
        
    Raises:
        ValueError: If DATABASE_URL is not set or invalid
    """
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Validate URL has required components
    if not database_url.startswith(("postgresql+asyncpg://", "postgresql://", "postgres://")):
        raise ValueError(
            "DATABASE_URL must use PostgreSQL with asyncpg driver "
            "(postgresql+asyncpg://) or will be converted automatically"
        )
    
    # Convert standard postgresql:// to postgresql+asyncpg:// for async support
    if database_url.startswith("postgresql://") and not database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    return database_url


async def create_engine_with_retry(
    database_url: str,
    max_retries: int = 3,
    initial_backoff: float = 0.5,
) -> AsyncEngine:
    """
    Create async engine with connection retry logic.
    
    Implements exponential backoff for transient connection failures.
    
    Args:
        database_url: PostgreSQL connection URL
        max_retries: Maximum number of connection attempts (default: 3)
        initial_backoff: Initial backoff delay in seconds (default: 0.5)
        
    Returns:
        AsyncEngine: Configured async SQLAlchemy engine
        
    Raises:
        OperationalError: If connection fails after all retries
    """
    backoff = initial_backoff
    last_error = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Creating database engine (attempt {attempt + 1}/{max_retries})")
            
            engine = create_async_engine(
                database_url,
                echo=False,  # Set to True for SQL query logging in development
                pool_size=10,  # Number of connections to keep in pool
                max_overflow=10,  # Additional connections when pool is full
                pool_timeout=30,  # Seconds to wait for connection from pool
                pool_pre_ping=True,  # Verify connections before using them
                pool_recycle=3600,  # Recycle connections after 1 hour
            )
            
            # Test the connection
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
                logger.info("Database engine created and connection verified")
                return engine
                
        except OperationalError as e:
            last_error = e
            logger.warning(
                f"Database connection attempt {attempt + 1} failed: {str(e)}"
            )
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {backoff} seconds...")
                await asyncio.sleep(backoff)
                backoff *= 2  # Exponential backoff
            else:
                logger.error(
                    f"Failed to connect to database after {max_retries} attempts"
                )
                raise last_error from e
    
    # This should never be reached, but satisfies type checker
    raise last_error if last_error else OperationalError("Failed to create engine")


def init_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Initialize global database engine.
    
    This should be called once during application startup.
    
    Args:
        database_url: Optional database URL. If not provided, loads from environment.
        
    Returns:
        AsyncEngine: The initialized engine instance
    """
    global _engine, _session_factory
    
    if _engine is not None:
        logger.warning("Database engine already initialized")
        return _engine
    
    # Get and validate database URL
    db_url = database_url or get_database_url()
    
    # Create engine synchronously by running async function
    # Note: This should be called from an async context in production
    try:
        _engine = asyncio.get_event_loop().run_until_complete(
            create_engine_with_retry(db_url)
        )
    except RuntimeError:
        # If no event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _engine = loop.run_until_complete(create_engine_with_retry(db_url))
    
    # Create session factory
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire objects after commit
        autoflush=False,  # Explicit flushing for better control
        autocommit=False,  # Explicit commits for transaction safety
    )
    
    logger.info("Database engine and session factory initialized")
    return _engine


def get_engine() -> AsyncEngine:
    """
    Get the global database engine instance.
    
    Returns:
        AsyncEngine: The engine instance
        
    Raises:
        RuntimeError: If engine has not been initialized
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. Call init_engine() first."
        )
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    This is a FastAPI dependency that provides a database session
    with proper lifecycle management.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    Yields:
        AsyncSession: Database session
    """
    if _session_factory is None:
        raise RuntimeError(
            "Session factory not initialized. Call init_engine() first."
        )
    
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_engine() -> None:
    """
    Close the database engine and clean up connections.
    
    This should be called during application shutdown.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        logger.info("Closing database engine")
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")
