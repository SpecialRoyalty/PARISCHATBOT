from __future__ import annotations
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models import InviteLink
from app.config import get_settings
settings=get_settings(); router=Router()

@router.callback_query(F.data=='invite:get')
async def get_invite(c:CallbackQuery, bot:Bot):
    async with SessionLocal() as session:
        existing=(await session.execute(select(InviteLink).where(InviteLink.user_id==c.from_user.id))).scalar_one_or_none()
        if existing:
            link=existing.link
        else:
            inv=await bot.create_chat_invite_link(settings.GROUP_ID, name=f'invite_{c.from_user.id}', creates_join_request=False)
            code=inv.invite_link.rsplit('/',1)[-1]
            session.add(InviteLink(code=code,user_id=c.from_user.id,link=inv.invite_link)); await session.commit(); link=inv.invite_link
    try:
        await bot.send_message(c.from_user.id, f'Voici ton lien unique d’invitation :\n{link}')
        await c.answer('Lien envoyé en privé.')
    except Exception:
        await c.answer('Démarre le bot en privé pour recevoir ton lien.',show_alert=True)
