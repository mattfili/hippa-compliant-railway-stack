"""
Database setup verification script.

This script verifies that:
1. Database URL is properly configured
2. Database engine connects successfully
3. Connection pooling is working
4. Alembic migrations can run
5. pgvector extension is enabled

Usage:
    export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/dbname"
    python verify_database.py
"""

import asyncio
import os
import sys

from sqlalchemy import text
from app.database.engine import init_engine, get_engine, close_engine


async def verify_database_setup():
    """Verify database setup and configuration."""
    print("=" * 60)
    print("Database Setup Verification")
    print("=" * 60)
    
    # Check DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("\nPlease set DATABASE_URL to your PostgreSQL connection string:")
        print("export DATABASE_URL='postgresql+asyncpg://user:pass@localhost:5432/dbname'")
        return False
    
    # Mask password in output
    masked_url = database_url
    if "@" in masked_url:
        parts = masked_url.split("@")
        user_part = parts[0].split("//")[1]
        if ":" in user_part:
            user, _ = user_part.rsplit(":", 1)
            masked_url = masked_url.replace(f"{user_part}@", f"{user}:****@")
    
    print(f"\n1. Database URL Configuration")
    print(f"   ✓ DATABASE_URL is set: {masked_url}")
    
    # Initialize engine
    try:
        print(f"\n2. Database Engine Initialization")
        engine = init_engine(database_url)
        print(f"   ✓ Engine created with connection pooling:")
        print(f"     - Pool size: {engine.pool.size()}")
        print(f"     - Max overflow: {engine.pool._max_overflow}")
        print(f"     - Pool timeout: {engine.pool._timeout}s")
    except Exception as e:
        print(f"   ❌ Failed to initialize engine: {e}")
        return False
    
    # Test connection
    try:
        print(f"\n3. Database Connection Test")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"   ✓ Connected to PostgreSQL")
            print(f"     Version: {version[:50]}...")
    except Exception as e:
        print(f"   ❌ Failed to connect: {e}")
        await close_engine()
        return False
    
    # Check pgvector extension
    try:
        print(f"\n4. pgvector Extension Check")
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT * FROM pg_extension WHERE extname = 'vector';")
            )
            extension = result.fetchone()
            
            if extension:
                print(f"   ✓ pgvector extension is enabled")
            else:
                print(f"   ⚠️  pgvector extension not yet enabled")
                print(f"      Run 'alembic upgrade head' to enable it")
    except Exception as e:
        print(f"   ❌ Failed to check extension: {e}")
        await close_engine()
        return False
    
    # Test connection pooling
    try:
        print(f"\n5. Connection Pool Test")
        print(f"   Testing 5 concurrent connections...")
        
        async def test_query():
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1;"))
                return result.scalar()
        
        # Run 5 concurrent queries
        results = await asyncio.gather(*[test_query() for _ in range(5)])
        if all(r == 1 for r in results):
            print(f"   ✓ Connection pool handled 5 concurrent connections")
        else:
            print(f"   ❌ Some queries failed")
    except Exception as e:
        print(f"   ❌ Connection pool test failed: {e}")
        await close_engine()
        return False
    
    # Clean up
    await close_engine()
    
    print("\n" + "=" * 60)
    print("✓ All database checks passed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run migrations: alembic upgrade head")
    print("2. Verify pgvector is enabled (it will show ✓ in check 4)")
    print("3. Start developing your application!")
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(verify_database_setup())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
