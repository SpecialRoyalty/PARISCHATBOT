from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, ChatPermissions
from app.config import settings
from app.services.moderation import LINK_RE, has_forbidden, log, hash_message_media, media_is_banned, add_media_hash
from app.services.roles import is_trusted
from app.services.users import upsert_user
from datetime import timedelta
router=Router()

@router.message(F.chat.id==settings.GROUP_ID, F.new_chat_members)
async def join_msg(m:Message):
    try: await m.delete()
    except Exception: pass
    for u in m.new_chat_members: await upsert_user(u)
@router.message(F.chat.id==settings.GROUP_ID, F.left_chat_member)
async def left_msg(m:Message):
    try: await m.delete()
    except Exception: pass
@router.my_chat_member()
async def my_chat_member(upd:ChatMemberUpdated, bot):
    if upd.chat.type in {'group','supergroup'} and upd.chat.id!=settings.GROUP_ID:
        await log('BOT_ADDED_UNAUTHORIZED', upd.from_user.id, str(upd.chat.id))
        try: await bot.leave_chat(upd.chat.id)
        except Exception: pass

@router.message(F.chat.id==settings.GROUP_ID)
async def group_guard(m:Message, bot):
    if m.from_user: await upsert_user(m.from_user)
    # service messages only
    if m.new_chat_members or m.left_chat_member: return
    text=m.text or m.caption or ''
    # trusted commands
    if text.startswith('/supprime') and await is_trusted(m.from_user.id):
        if m.reply_to_message:
            try: await m.reply_to_message.delete()
            except Exception: pass
        try: await m.delete()
        except Exception: pass
        return
    if text.startswith('/ban') and await is_trusted(m.from_user.id):
        if m.reply_to_message and m.reply_to_message.from_user:
            h,t=await hash_message_media(bot,m.reply_to_message)
            if h: await add_media_hash(h,t,m.from_user.id)
            try: await bot.ban_chat_member(settings.GROUP_ID,m.reply_to_message.from_user.id)
            except Exception: pass
            try: await m.reply_to_message.delete()
            except Exception: pass
        try: await m.delete()
        except Exception: pass
        return
    # links
    if LINK_RE.search(text):
        try: await m.delete()
        except Exception: pass
        try: await bot.ban_chat_member(settings.GROUP_ID,m.from_user.id)
        except Exception: pass
        await log('LINK_BAN',m.from_user.id,text[:200]); return
    # commands non autorisées dans le groupe
    # /start dans le groupe ne doit jamais déclencher de panel public.
    # Admin/Trusted/Super : suppression silencieuse, pas de sanction.
    # Utilisateur normal : suppression + sanction silencieuse.
    if text.startswith('/'):
        try: await m.delete()
        except Exception: pass
        if await is_trusted(m.from_user.id):
            await log('COMMAND_DELETED_ALLOWED_ROLE', m.from_user.id, text[:100])
            return
        try:
            await bot.restrict_chat_member(
                settings.GROUP_ID,
                m.from_user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except Exception: pass
        await log('COMMAND_MUTE',m.from_user.id,text[:100]); return
    # forbidden words
    w=await has_forbidden(text)
    if w:
        try: await m.delete()
        except Exception: pass
        await log('FORBIDDEN_WORD',m.from_user.id,w); return
    # media hash
    h,t=await hash_message_media(bot,m)
    if h and await media_is_banned(h):
        try: await m.delete()
        except Exception: pass
        try: await bot.ban_chat_member(settings.GROUP_ID,m.from_user.id)
        except Exception: pass
        await log('MEDIA_HASH_BAN',m.from_user.id,h); return
