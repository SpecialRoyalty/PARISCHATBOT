import hashlib, re
from datetime import datetime, timedelta
from sqlalchemy import select, func
from aiogram.types import Message
from app.db.session import SessionLocal
from app.db.models import ForbiddenWord, MediaHash, SecurityLog

LINK_RE=re.compile(r'(https?://|t\.me/|telegram\.me/|www\.|[a-z0-9-]+\.[a-z]{2,})', re.I)

async def log(event,user_id=None,details=None):
    async with SessionLocal() as s:
        s.add(SecurityLog(event=event,user_id=user_id,details=details)); await s.commit()
async def add_word(word, uid=None):
    # Retourne: "added", "exists" ou "empty".
    clean = (word or '').strip()
    if not clean:
        return 'empty'
    async with SessionLocal() as s:
        existing = (await s.execute(
            select(ForbiddenWord).where(func.lower(ForbiddenWord.word) == clean.lower())
        )).scalar_one_or_none()
        if existing:
            return 'exists'
        s.add(ForbiddenWord(word=clean, added_by=uid))
        await s.commit()
        return 'added'
async def list_words():
    async with SessionLocal() as s:
        return (await s.execute(select(ForbiddenWord).order_by(ForbiddenWord.word))).scalars().all()
async def delete_word(wid:int):
    async with SessionLocal() as s:
        x=await s.get(ForbiddenWord,wid)
        if x: await s.delete(x); await s.commit(); return True
        return False
async def has_forbidden(text:str):
    if not text: return None
    async with SessionLocal() as s:
        words=(await s.execute(select(ForbiddenWord))).scalars().all()
        low=text.lower()
        for w in words:
            if w.word.lower() in low: return w.word
    return None
async def add_media_hash(h, media_type, uid=None):
    async with SessionLocal() as s:
        if not (await s.execute(select(MediaHash).where(MediaHash.hash==h))).scalar_one_or_none():
            s.add(MediaHash(hash=h,media_type=media_type,added_by=uid)); await s.commit()
async def list_hashes():
    async with SessionLocal() as s: return (await s.execute(select(MediaHash).order_by(MediaHash.id.desc()))).scalars().all()
async def delete_hash(hid:int):
    async with SessionLocal() as s:
        x=await s.get(MediaHash,hid)
        if x: await s.delete(x); await s.commit(); return True
        return False
async def hash_bytes(data:bytes)->str: return hashlib.sha256(data).hexdigest()
async def hash_message_media(bot, msg:Message):
    file_id=None; typ=None
    if msg.photo: file_id=msg.photo[-1].file_id; typ='photo'
    elif msg.video: file_id=msg.video.file_id; typ='video'
    elif msg.document: file_id=msg.document.file_id; typ='document'
    if not file_id: return None,None
    f=await bot.get_file(file_id); buf=await bot.download_file(f.file_path)
    data=buf.read()
    if typ=='video': data=data[:1024*1024]
    return hashlib.sha256(data).hexdigest(), typ
async def media_is_banned(h):
    async with SessionLocal() as s:
        return bool((await s.execute(select(MediaHash).where(MediaHash.hash==h))).scalar_one_or_none())
