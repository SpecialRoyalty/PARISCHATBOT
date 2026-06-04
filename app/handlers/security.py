from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from app.config import get_settings
from app.db.session import SessionLocal
from app.services.common import log
settings=get_settings(); router=Router()

@router.my_chat_member()
async def bot_added(event:ChatMemberUpdated, bot:Bot):
    if event.chat.id != settings.GROUP_ID and event.new_chat_member.status in {'member','administrator'}:
        async with SessionLocal() as session:
            await log(session,'BOT_ADDED_UNAUTHORIZED', event.from_user.id if event.from_user else None, event.chat.id, 'Bot ajouté hors groupe autorisé')
        for aid in settings.admin_ids:
            try: await bot.send_message(aid, f'⚠️ Bot ajouté dans un groupe non autorisé : {event.chat.id}. Ajout par : {event.from_user.id if event.from_user else "inconnu"}. Je quitte le groupe.')
            except Exception: pass
        try: await bot.leave_chat(event.chat.id)
        except Exception: pass
