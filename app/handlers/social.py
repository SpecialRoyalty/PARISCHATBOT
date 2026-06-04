from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from app.config import settings
from app.db.session import SessionLocal
from app.db.models import Suggestion, User, InviteLink
from app.services.core import get_or_create_invite

router=Router()
sugg_state={}

def share_keyboard(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Je partage', callback_data='share:get')]])
def suggest_keyboard(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Suggérer un match', callback_data='suggest:start')]])

@router.callback_query(F.data=='share:get')
async def share(cb:CallbackQuery, bot:Bot):
    link=await get_or_create_invite(bot, cb.from_user.id)
    await cb.message.answer(f'📢 Voici ton lien unique :\n{link}')
    await cb.answer()

@router.callback_query(F.data=='suggest:start')
async def sug_start(cb:CallbackQuery):
    sugg_state[cb.from_user.id]={'step':'category'}
    await cb.message.answer('Catégorie ? Foot / Basket / Tennis / Boxe / Autre')
    await cb.answer()

@router.message(F.chat.type=='private')
async def sug_text(message:Message, bot:Bot):
    st=sugg_state.get(message.from_user.id)
    if not st: return
    if st['step']=='category': st['category']=message.text.strip(); st['step']='title'; await message.answer('Titre du match ?'); return
    if st['step']=='title': st['title']=message.text.strip(); st['step']='date'; await message.answer('Date/heure si connue ?'); return
    if st['step']=='date': st['date']=message.text.strip(); st['step']='photo'; await message.answer('Image optionnelle : envoie une photo ou écris SKIP.'); return
    if st['step']=='photo':
        photo=message.photo[-1].file_id if message.photo else None
        async with SessionLocal() as s:
            obj=Suggestion(user_id=message.from_user.id,category=st['category'],title=st['title'],proposed_date=st['date'],photo_file_id=photo)
            s.add(obj); await s.commit(); await s.refresh(obj)
        for aid in settings.admin_ids:
            try: await bot.send_message(aid, f'💡 Nouvelle suggestion #{obj.id}\nCatégorie: {obj.category}\nMatch: {obj.title}\nDate: {obj.proposed_date}\nUtilisateur: {message.from_user.id}')
            except Exception: pass
        sugg_state.pop(message.from_user.id,None); await message.answer('✅ Suggestion envoyée à la modération.')
