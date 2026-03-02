"""
Database connection and session management.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from app.core.config import get_settings

settings = get_settings()

import urllib.parse

# Safely handle passwords with special characters in the DATABASE_URL
def get_safe_engine():
    db_url = settings.DATABASE_URL
    if "://" in db_url:
        # Split into scheme and the rest
        scheme, rest = db_url.split("://", 1)
        if "@" in rest:
            # Handle user:pass@host
            auth_part, host_part = rest.rsplit("@", 1)
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
                # Re-encode just the password to be safe
                safe_password = urllib.parse.quote_plus(urllib.parse.unquote(password))
                db_url = f"{scheme}://{user}:{safe_password}@{host_part}"

    return create_async_engine(
        db_url,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,   # Recycle connections every 30 min (MySQL default wait_timeout=28800)
        pool_timeout=30,     # Wait max 30s for a connection from the pool
    )

engine = get_safe_engine()


# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection(db: AsyncSession) -> bool:
    """Check if database connection is alive."""
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
