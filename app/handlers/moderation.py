from __future__ import annotations
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models import ForbiddenWord, MediaHash, User, Invitation, Badge
from app.services.common import upsert_user, has_link, is_trusted, log
from app.services.media_hashing import compute_media_hash
from app.config import get_settings
settings=get_settings(); router=Router()

async def silent_delete(m:Message):
    try: await m.delete()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning('delete_failed chat=%s message=%s error=%s', getattr(getattr(m,'chat',None),'id',None), getattr(m,'message_id',None), e)


def is_service_message(m: Message) -> bool:
    """Détecte les messages système Telegram à supprimer immédiatement.
    Inclut entrées/sorties, ajout via lien, changements de groupe et notifications
    générées par certaines actions admin selon le client Telegram.
    """
    service_attrs = (
        'new_chat_members', 'left_chat_member', 'new_chat_title', 'new_chat_photo',
        'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created',
        'channel_chat_created', 'message_auto_delete_timer_changed', 'migrate_to_chat_id',
        'migrate_from_chat_id', 'pinned_message', 'connected_website',
        'proximity_alert_triggered', 'forum_topic_created', 'forum_topic_edited',
        'forum_topic_closed', 'forum_topic_reopened', 'general_forum_topic_hidden',
        'general_forum_topic_unhidden', 'write_access_allowed', 'users_shared',
        'chat_shared', 'boost_added', 'sender_boost_count', 'chat_background_set',
        'giveaway_created', 'giveaway', 'giveaway_winners', 'giveaway_completed',
        'video_chat_scheduled', 'video_chat_started', 'video_chat_ended',
        'video_chat_participants_invited', 'web_app_data'
    )
    return any(getattr(m, attr, None) for attr in service_attrs)


async def ban_user(bot:Bot, chat_id:int, user_id:int):
    try: await bot.ban_chat_member(chat_id,user_id)
    except Exception: pass
    async with SessionLocal() as session:
        u=await session.get(User,user_id)
        if u: u.banned=True; await session.commit()

async def mute_user(bot:Bot, chat_id:int, user_id:int, days:int):
    from aiogram.types import ChatPermissions
    until=datetime.utcnow()+timedelta(days=days)
    try:
        await bot.restrict_chat_member(chat_id,user_id,permissions=ChatPermissions(can_send_messages=False),until_date=until)
    except Exception: pass
    async with SessionLocal() as session:
        u=await session.get(User,user_id)
        if u: u.muted_until=until; await session.commit()


@router.message(F.chat.type.in_({'group','supergroup'}))
async def delete_join_leave_service_messages(m: Message, bot: Bot):
    """Supprime en priorité tous les messages système Telegram.
    Important : le bot doit être administrateur avec le droit Supprimer les messages.
    """
    if not is_service_message(m):
        return
    if m.chat.id != settings.GROUP_ID:
        await silent_delete(m)
        try:
            await bot.leave_chat(m.chat.id)
        except Exception:
            pass
        return
    # enregistrer invitations si possible
    if m.new_chat_members and m.invite_link and m.invite_link.invite_link:
        async with SessionLocal() as session:
            from app.db.models import InviteLink
            il=(await session.execute(select(InviteLink).where(InviteLink.link==m.invite_link.invite_link))).scalar_one_or_none()
            if il:
                for user in m.new_chat_members:
                    if not user.is_bot and user.id != il.user_id:
                        try:
                            session.add(Invitation(inviter_id=il.user_id,invited_id=user.id))
                            from sqlalchemy import func
                            count = (await session.execute(select(func.count(Invitation.id)).where(Invitation.inviter_id==il.user_id))).scalar() or 0
                            count += 1
                            for threshold, badge in [(5,'🥉 Ambassadeur Bronze'),(25,'🥈 Ambassadeur Argent'),(50,'🥇 Ambassadeur Or')]:
                                if count >= threshold and not await session.get(Badge, {'user_id':il.user_id,'badge':badge}):
                                    session.add(Badge(user_id=il.user_id,badge=badge))
                            await session.commit()
                        except Exception:
                            await session.rollback()
    await silent_delete(m)
    if m.new_chat_members and any(u.is_bot for u in m.new_chat_members) and m.from_user:
        await ban_user(bot,m.chat.id,m.from_user.id)

@router.message(F.chat.type.in_({'group','supergroup'}))
async def moderate_group(m:Message, bot:Bot):
    # groupe non autorisé
    if m.chat.id != settings.GROUP_ID:
        await silent_delete(m)
        async with SessionLocal() as session: await log(session,'UNAUTHORIZED_GROUP',m.from_user.id if m.from_user else None,m.chat.id,'Bot utilisé dans groupe non autorisé')
        for aid in settings.admin_ids:
            try: await bot.send_message(aid, f'⚠️ Tentative d’utilisation du bot dans un groupe non autorisé : {m.chat.id}')
            except Exception: pass
        try: await bot.leave_chat(m.chat.id)
        except Exception: pass
        return
    if m.from_user:
        async with SessionLocal() as session: await upsert_user(session,m.from_user,bot)
    # supprimer notifications système
    if m.new_chat_members or m.left_chat_member:
        # enregistrer invitations si possible
        if m.new_chat_members and m.invite_link and m.invite_link.invite_link:
            async with SessionLocal() as session:
                from app.db.models import InviteLink
                il=(await session.execute(select(InviteLink).where(InviteLink.link==m.invite_link.invite_link))).scalar_one_or_none()
                if il:
                    for user in m.new_chat_members:
                        if not user.is_bot and user.id != il.user_id:
                            try:
                                session.add(Invitation(inviter_id=il.user_id,invited_id=user.id))
                                from sqlalchemy import func
                                count = (await session.execute(select(func.count(Invitation.id)).where(Invitation.inviter_id==il.user_id))).scalar() or 0
                                count += 1
                                for threshold, badge in [(5,'🥉 Ambassadeur Bronze'),(25,'🥈 Ambassadeur Argent'),(50,'🥇 Ambassadeur Or')]:
                                    if count >= threshold and not await session.get(Badge, {'user_id':il.user_id,'badge':badge}):
                                        session.add(Badge(user_id=il.user_id,badge=badge))
                                await session.commit()
                            except Exception: await session.rollback()
        await silent_delete(m)
        # bot ajouté interdit
        if m.new_chat_members and any(u.is_bot for u in m.new_chat_members):
            await ban_user(bot,m.chat.id,m.from_user.id)
        return
    txt=m.text or m.caption or ''
    if txt.startswith('/'):
        async with SessionLocal() as session:
            trusted=await is_trusted(session,m.from_user.id)
        if txt.split()[0] in ['/supprime','/ban'] and trusted and m.reply_to_message:
            await silent_delete(m)
            if txt.split()[0]=='/supprime':
                await silent_delete(m.reply_to_message)
            else:
                target=m.reply_to_message.from_user
                media=m.reply_to_message
                media_hash = await compute_media_hash(bot, media)
                async with SessionLocal() as session:
                    if media_hash and not await session.get(MediaHash, media_hash): session.add(MediaHash(hash=media_hash,created_by=m.from_user.id,note='trusted ban media'))
                    await session.commit(); await log(session,'TRUSTED_BAN',target.id if target else None,m.chat.id,'trusted command')
                await silent_delete(media)
                if target: await ban_user(bot,m.chat.id,target.id)
            return
        await silent_delete(m)
        async with SessionLocal() as session:
            u=await session.get(User,m.from_user.id) or await upsert_user(session,m.from_user,bot)
            u.command_violations+=1; await session.commit(); await log(session,'COMMAND_USED',m.from_user.id,m.chat.id,txt[:200])
            if u.command_violations>=2: await ban_user(bot,m.chat.id,m.from_user.id)
            else: await mute_user(bot,m.chat.id,m.from_user.id,10)
        return
    if settings.FORBID_LINKS and has_link(txt):
        await silent_delete(m); await ban_user(bot,m.chat.id,m.from_user.id)
        async with SessionLocal() as session: await log(session,'LINK_BAN',m.from_user.id,m.chat.id,txt[:500])
        return
    async with SessionLocal() as session:
        words=[w.word for w in (await session.execute(select(ForbiddenWord))).scalars().all()]
        bad=next((w for w in words if w and w in txt.lower()),None)
        if bad:
            await silent_delete(m)
            u=await session.get(User,m.from_user.id) or await upsert_user(session,m.from_user,bot)
            u.word_violations+=1; n=u.word_violations; await session.commit(); await log(session,'FORBIDDEN_WORD',m.from_user.id,m.chat.id,bad)
            if n==1: await mute_user(bot,m.chat.id,m.from_user.id,1)
            elif n==2: await mute_user(bot,m.chat.id,m.from_user.id,3)
            else: await ban_user(bot,m.chat.id,m.from_user.id)
            return
    if m.photo or m.video or m.document or m.animation or m.sticker:
        media_hash = await compute_media_hash(bot, m)
        async with SessionLocal() as session:
            if media_hash and await session.get(MediaHash, media_hash):
                await silent_delete(m); await ban_user(bot,m.chat.id,m.from_user.id); await log(session,'BANNED_MEDIA',m.from_user.id,m.chat.id,'blocked media')
                return

@router.message(F.text.in_(['/supprime','/ban']))
async def trusted_commands(m:Message, bot:Bot):
    async with SessionLocal() as session:
        allowed=await is_trusted(session,m.from_user.id)
    if not allowed: return
    await silent_delete(m)
    if not m.reply_to_message: return
    target=m.reply_to_message.from_user
    if m.text=='/supprime':
        await silent_delete(m.reply_to_message)
    elif m.text=='/ban' and target:
        # si réponse à média, l’interdire pour futur
        media=m.reply_to_message
        media_hash = await compute_media_hash(bot, media)
        async with SessionLocal() as session:
            if media_hash and not await session.get(MediaHash, media_hash): session.add(MediaHash(hash=media_hash,created_by=m.from_user.id,note='trusted ban media'))
            await session.commit(); await log(session,'TRUSTED_BAN',target.id,m.chat.id,'trusted command')
        await silent_delete(media); await ban_user(bot,m.chat.id,target.id)
