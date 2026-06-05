from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.db.models import Base, Role
from sqlalchemy import select

engine = create_async_engine(settings.db_url_async, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # seed env roles in DB
    async with SessionLocal() as s:
        for uid in settings.super_admin_ids:
            if not await s.get(Role, {'user_id':uid,'role':'super_admin'}): s.add(Role(user_id=uid, role='super_admin'))
        for uid in settings.admin_ids:
            if not await s.get(Role, {'user_id':uid,'role':'admin'}): s.add(Role(user_id=uid, role='admin'))
        for uid in settings.trusted_ids:
            if not await s.get(Role, {'user_id':uid,'role':'trusted'}): s.add(Role(user_id=uid, role='trusted'))
        await s.commit()
