from datetime import datetime, timedelta
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models import User, UsernameHistory
from app.config import settings
from app.utils.text import anonymize

async def upsert_user(tg_user, bot=None):
    async with SessionLocal() as s:
        u=await s.get(User,tg_user.id)
        now=datetime.utcnow()
        if not u:
            u=User(id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name, last_name=tg_user.last_name, last_seen_at=now)
            s.add(u); await s.commit(); return u, []
        changes=[]
        for field,new in [('username',tg_user.username),('first_name',tg_user.first_name),('last_name',tg_user.last_name)]:
            old=getattr(u,field)
            if old!=new:
                s.add(UsernameHistory(user_id=u.id, old_value=old, new_value=new, field=field))
                setattr(u,field,new); changes.append((field,old,new))
        u.last_seen_at=now
        await s.commit(); return u, changes

async def all_users():
    async with SessionLocal() as s:
        res=await s.execute(select(User)); return res.scalars().all()
