from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings


def make_async_database_url(url: str) -> str:
    """Railway often exposes PostgreSQL as postgresql://...
    SQLAlchemy async engine needs the asyncpg dialect: postgresql+asyncpg://...
    Also supports postgres://... aliases.
    """
    if not url:
        raise RuntimeError("DATABASE_URL is missing")
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        return url
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


settings = get_settings()
DATABASE_URL = make_async_database_url(settings.DATABASE_URL)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
