from __future__ import annotations
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from aiogram import Bot
from aiogram.types import Message, User as TgUser
from app.config import get_settings
from app.db.models import User, IdentityHistory, SecurityLog, Role, Setting, ScheduledMessage

settings = get_settings()

URL_RE = re.compile(r'(https?://|t\.me/|telegram\.me/|www\.|[a-z0-9-]+\.(com|fr|net|org|io|gg|me|co|app)\b)', re.I)
SCORE_RE = re.compile(r'^\s*\d{1,2}\s*[-:]\s*\d{1,2}\s*$')

def now_utc(): return datetime.utcnow()
def local_dt_str(dt: datetime):
    try:
        return dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(settings.TIMEZONE)).strftime('%d %B %Y à %Hh%M')
    except Exception:
        return dt.strftime('%d/%m/%Y à %Hh%M')

def anonymize(name: str | None) -> str:
    if not name: return 'Membre****'
    s = name.strip() or 'Membre'
    if len(s) <= 2: return s[0]+'*'
    if len(s) <= 5: return s[0]+'***'+s[-1]
    return s[:2]+'****'+s[-1]

def full_name(tg: TgUser) -> str:
    return ' '.join(x for x in [tg.first_name, tg.last_name] if x) or (tg.username or str(tg.id))

def has_link(text: str | None) -> bool:
    return bool(text and URL_RE.search(text))

async def log(session, event: str, user_id: int | None=None, chat_id: int | None=None, details: str=''):
    session.add(SecurityLog(event=event, user_id=user_id, chat_id=chat_id, details=details[:4000]))
    await session.commit()

async def upsert_user(session, tg: TgUser, bot: Bot | None=None):
    u = await session.get(User, tg.id)
    nm = full_name(tg)
    if not u:
        u = User(id=tg.id, username=tg.username, first_name=tg.first_name, last_name=tg.last_name, is_bot=tg.is_bot)
        session.add(u); await session.commit(); return u
    old_name = ' '.join(x for x in [u.first_name, u.last_name] if x) or (u.username or str(u.id))
    changed = (u.username != tg.username) or (old_name != nm)
    if changed:
        session.add(IdentityHistory(user_id=tg.id, old_username=u.username, new_username=tg.username, old_name=old_name, new_name=nm))
        cooldown = timedelta(hours=settings.IDENTITY_PUBLIC_COOLDOWN_HOURS)
        if bot and (not u.public_identity_alert_at or now_utc() - u.public_identity_alert_at > cooldown):
            try:
                await bot.send_message(settings.GROUP_ID, f"🔄 Changement d'identité détecté\n\n👤 Utilisateur : {anonymize(old_name)}\nAncien : {anonymize(old_name)}\nNouveau : {anonymize(nm)}\n\n⚠️ Vérifiez toujours l'identité des membres avant tout échange privé.")
                u.public_identity_alert_at = now_utc()
            except Exception: pass
    u.username=tg.username; u.first_name=tg.first_name; u.last_name=tg.last_name; u.is_bot=tg.is_bot; u.last_seen_at=now_utc()
    await session.commit(); return u

async def is_super(session, user_id:int) -> bool:
    if user_id in settings.super_admin_ids: return True
    r = await session.get(Role, {'user_id': user_id, 'role': 'super_admin'})
    return bool(r)
async def is_admin(session, user_id:int) -> bool:
    if user_id in settings.admin_ids or await is_super(session,user_id): return True
    r = await session.get(Role, {'user_id': user_id, 'role': 'admin'})
    return bool(r)
async def is_trusted(session, user_id:int) -> bool:
    if user_id in settings.trusted_ids or await is_admin(session,user_id): return True
    r = await session.get(Role, {'user_id': user_id, 'role': 'trusted'})
    return bool(r)

async def get_setting(session, key:str, default:str='') -> str:
    s=await session.get(Setting,key); return s.value if s else default
async def set_setting(session,key:str,value:str):
    s=await session.get(Setting,key)
    if not s: session.add(Setting(key=key,value=value))
    else: s.value=value
    await session.commit()

async def replace_group_message(bot:Bot, session, key:str, text:str, reply_markup=None, photo_file_id:str|None=None):
    sm=await session.get(ScheduledMessage,key)
    if sm and sm.message_id:
        try: await bot.delete_message(settings.GROUP_ID, sm.message_id)
        except Exception: pass
    if photo_file_id:
        msg=await bot.send_photo(settings.GROUP_ID, photo_file_id, caption=text, reply_markup=reply_markup)
    else:
        msg=await bot.send_message(settings.GROUP_ID, text, reply_markup=reply_markup)
    if not sm:
        sm=ScheduledMessage(key=key); session.add(sm)
    sm.message_id=msg.message_id; sm.sent_at=now_utc(); await session.commit(); return msg
