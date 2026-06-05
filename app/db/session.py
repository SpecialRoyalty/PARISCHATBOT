from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.db.models import Base, Role, ForbiddenWord
from sqlalchemy import select

engine = create_async_engine(settings.db_url_async, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def cleanup_forbidden_words_startup(s: AsyncSession):
    """Nettoie les doublons de mots interdits créés manuellement en DB.
    On garde le premier ID et on supprime les doublons insensibles à la casse.
    """
    words = (await s.execute(select(ForbiddenWord).order_by(ForbiddenWord.id.asc()))).scalars().all()
    seen = set()
    changed = False
    for w in words:
        key = (w.word or '').strip().lower()
        if not key or key in seen:
            await s.delete(w)
            changed = True
        else:
            seen.add(key)
    if changed:
        await s.commit()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        for uid in settings.super_admin_ids:
            if not await s.get(Role, {'user_id': uid, 'role': 'super_admin'}):
                s.add(Role(user_id=uid, role='super_admin'))
        for uid in settings.admin_ids:
            if not await s.get(Role, {'user_id': uid, 'role': 'admin'}):
                s.add(Role(user_id=uid, role='admin'))
        for uid in settings.trusted_ids:
            if not await s.get(Role, {'user_id': uid, 'role': 'trusted'}):
                s.add(Role(user_id=uid, role='trusted'))
        await s.commit()
        await cleanup_forbidden_words_startup(s)
