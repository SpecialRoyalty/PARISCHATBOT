from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command
from datetime import datetime, timedelta
from sqlalchemy import select
from app.config import settings
from app.db.session import SessionLocal
from app.db.models import ForbiddenWord, Sanction, MediaHash, User, InviteLink
from app.utils.text import has_link
from app.services.core import upsert_user, log
import hashlib
from io import BytesIO

router=Router()

async def safe_delete(message: Message):
    try: await message.delete()
    except Exception: pass

async def media_hash_from_message(message: Message, bot: Bot) -> tuple[str,str] | None:
    file_id=None; mtype=None
    if message.photo:
        file_id=message.photo[-1].file_id; mtype='photo'
    elif message.video:
        file_id=message.video.file_id; mtype='video'
    elif message.document:
        file_id=message.document.file_id; mtype='document'
    if not file_id: return None
    f=await bot.get_file(file_id)
    bio=BytesIO(); await bot.download_file(f.file_path, bio)
    data=bio.getvalue()
    if mtype=='video': data=data[:1024*1024]
    return hashlib.sha256(data).hexdigest(), mtype

async def sanction(bot:Bot, chat_id:int, user_id:int, kind:str):
    until=None
    async with SessionLocal() as s:
        obj=(await s.execute(select(Sanction).where(Sanction.user_id==user_id,Sanction.kind==kind))).scalar_one_or_none()
        if not obj:
            obj=Sanction(user_id=user_id,kind=kind,count=1); s.add(obj)
        else: obj.count+=1
        c=obj.count; await s.commit()
    if kind=='forbidden_word':
        if c==1: until=datetime.utcnow()+timedelta(days=1)
        elif c==2: until=datetime.utcnow()+timedelta(days=3)
        else:
            await bot.ban_chat_member(chat_id,user_id); return
        await bot.restrict_chat_member(chat_id,user_id, permissions={'can_send_messages':False}, until_date=until)
    elif kind=='command':
        if c==1: await bot.restrict_chat_member(chat_id,user_id, permissions={'can_send_messages':False}, until_date=datetime.utcnow()+timedelta(days=10))
        else: await bot.ban_chat_member(chat_id,user_id)

@router.message(F.chat.id != settings.GROUP_ID, F.chat.type.in_({'group','supergroup'}))
async def wrong_group(message: Message, bot: Bot):
    for aid in settings.admin_ids:
        try: await bot.send_message(aid, f'🚨 Bot ajouté dans un groupe non autorisé : {message.chat.id} par {message.from_user.id if message.from_user else "inconnu"}')
        except Exception: pass
    try: await bot.leave_chat(message.chat.id)
    except Exception: pass

@router.message(F.new_chat_members | F.left_chat_member)
async def service_join_leave(message: Message):
    # suppression ciblée uniquement du message système Telegram
    await safe_delete(message)
    # comptage invitations uniques quand Telegram fournit l'invite_link
    if message.new_chat_members and getattr(message, 'invite_link', None):
        async with SessionLocal() as s:
            link_obj=(await s.execute(select(InviteLink).where(InviteLink.link==message.invite_link.invite_link))).scalar_one_or_none()
            if link_obj:
                inviter=await s.get(User, link_obj.user_id)
                if inviter:
                    inviter.invites += len(message.new_chat_members)
                    await s.commit()

@router.message(F.chat.id == settings.GROUP_ID, F.from_user)
async def moderate(message: Message, bot: Bot):
    if message.from_user.id in settings.admin_ids or message.from_user.id in settings.trusted_ids:
        await upsert_user(message.from_user); return
    await upsert_user(message.from_user)
    text=message.text or message.caption or ''
    if has_link(text):
        await safe_delete(message)
        try: await bot.ban_chat_member(message.chat.id,message.from_user.id)
        except Exception: pass
        await log('link_ban', text[:500], message.from_user.id); return
    if text.startswith('/'):
        await safe_delete(message); await sanction(bot,message.chat.id,message.from_user.id,'command'); return
    mh=await media_hash_from_message(message, bot)
    if mh:
        h,t=mh
        async with SessionLocal() as s:
            blocked=await s.get(MediaHash,h)
        if blocked:
            await safe_delete(message)
            try: await bot.ban_chat_member(message.chat.id,message.from_user.id)
            except Exception: pass
            await log('media_hash_ban', t, message.from_user.id)
            return
    async with SessionLocal() as s:
        words=[w.word.lower() for w in (await s.execute(select(ForbiddenWord))).scalars().all()]
    if any(w and w in text.lower() for w in words):
        await safe_delete(message); await sanction(bot,message.chat.id,message.from_user.id,'forbidden_word'); return

@router.message(Command('supprime'))
async def cmd_delete(message: Message):
    if message.from_user.id not in settings.trusted_ids and message.from_user.id not in settings.admin_ids: return
    if message.reply_to_message: await safe_delete(message.reply_to_message)
    await safe_delete(message)

@router.message(Command('ban'))
async def cmd_ban(message: Message, bot: Bot):
    if message.from_user.id not in settings.trusted_ids and message.from_user.id not in settings.admin_ids: return
    if message.reply_to_message:
        mh=await media_hash_from_message(message.reply_to_message, bot)
        if mh:
            h,t=mh
            async with SessionLocal() as s:
                existing=await s.get(MediaHash,h)
                if not existing:
                    s.add(MediaHash(hash=h, media_type=t, added_by=message.from_user.id))
                    await s.commit()
        if message.reply_to_message.from_user:
            await bot.ban_chat_member(message.chat.id,message.reply_to_message.from_user.id)
        await safe_delete(message.reply_to_message)
    await safe_delete(message)
