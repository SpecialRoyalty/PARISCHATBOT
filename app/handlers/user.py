from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models import User, Match, Prediction
from app.config import settings
from app.keyboards import active_matches as active_kb, winner_keyboard, score_skip
from app.services.core import upsert_user, active_matches, get_setting, update_trend
from app.utils.text import valid_score

router=Router()
pending_scores: dict[int, tuple[int,str]] = {}

@router.message(CommandStart())
async def start(message: Message, bot: Bot):
    await upsert_user(message.from_user)
    payload = (message.text or '').split(maxsplit=1)[1] if message.text and len(message.text.split())>1 else ''
    if payload.startswith('vote_'):
        mid=int(payload.replace('vote_',''))
        await open_match_by_id(message, mid)
        return
    if message.from_user.id in settings.admin_ids:
        from app.keyboards import admin_panel
        await message.answer('✅ Panel admin', reply_markup=admin_panel(message.from_user.id in settings.super_admin_ids))
        return
    async with SessionLocal() as s:
        u=await s.get(User,message.from_user.id); first=not u.welcome_seen; u.started=True; u.welcome_seen=True; await s.commit()
    if first:
        welcome=await get_setting('welcome_text','Bienvenue dans le bot Pronostic Sport. Ici tu peux consulter les pronostics en cours, donner ton avis et participer aux classements du groupe.')
        photo=await get_setting('welcome_photo','')
        if photo:
            await message.answer_photo(photo, caption=welcome)
        else:
            await message.answer(welcome)
    matches=await active_matches()
    await message.answer('Voici les pronostics en cours. Tu peux ouvrir un match et donner ton avis.', reply_markup=active_kb(matches))

async def open_match_by_id(message: Message, mid:int):
    async with SessionLocal() as s:
        m=await s.get(Match,mid)
        if not m or m.status!='active' or m.vote_close_at<=datetime.utcnow():
            await message.answer('⛔ Ce pronostic est fermé.'); return
        existing=(await s.execute(select(Prediction).where(Prediction.match_id==mid,Prediction.user_id==message.from_user.id))).scalar_one_or_none()
        if existing:
            await message.answer('✅ Tu as déjà pronostiqué sur ce match.'); return
        text=f"🏟 {m.title}\n\nQui va gagner d’après vous ?"
        if m.photo_file_id: await message.answer_photo(m.photo_file_id, caption=text, reply_markup=winner_keyboard(m))
        else: await message.answer(text, reply_markup=winner_keyboard(m))

@router.callback_query(F.data.startswith('openmatch:'))
async def openmatch(cb: CallbackQuery):
    mid=int(cb.data.split(':')[1])
    await open_match_by_id(cb.message, mid)
    await cb.answer()

@router.callback_query(F.data.startswith('pick:'))
async def pick(cb: CallbackQuery):
    _, mid, winner = cb.data.split(':')
    mid=int(mid)
    async with SessionLocal() as s:
        m=await s.get(Match,mid)
        if not m or m.status!='active' or m.vote_close_at<=datetime.utcnow():
            await cb.answer('Pronostic fermé', show_alert=True); return
        existing=(await s.execute(select(Prediction).where(Prediction.match_id==mid,Prediction.user_id==cb.from_user.id))).scalar_one_or_none()
        if existing:
            await cb.answer('Déjà voté', show_alert=True); return
    pending_scores[cb.from_user.id]=(mid,winner)
    await cb.message.answer('🎯 Prédire le score exact ?\nFormat : 2-1', reply_markup=score_skip(mid))
    await cb.answer()

@router.callback_query(F.data.startswith('score_skip:'))
async def skip_score(cb: CallbackQuery, bot: Bot):
    mid=int(cb.data.split(':')[1])
    if cb.from_user.id not in pending_scores:
        await cb.answer('Session expirée', show_alert=True); return
    _, winner=pending_scores.pop(cb.from_user.id)
    await save_prediction(cb.from_user.id, mid, winner, None, bot)
    await cb.message.answer('✅ Pronostic enregistré.')
    await cb.answer()

@router.message(F.chat.type=='private')
async def private_text(message: Message, bot: Bot):
    if message.from_user.id in pending_scores and valid_score(message.text or ''):
        mid,winner=pending_scores.pop(message.from_user.id)
        await save_prediction(message.from_user.id, mid, winner, message.text.strip().replace(':','-'), bot)
        await message.answer('✅ Pronostic enregistré.')

async def save_prediction(user_id:int, mid:int, winner:str, score:str|None, bot:Bot):
    async with SessionLocal() as s:
        u=await s.get(User,user_id)
        if not u:
            u=User(id=user_id); s.add(u)
        p=Prediction(match_id=mid,user_id=user_id,winner=winner,score=score)
        s.add(p)
        try:
            await s.commit()
        except IntegrityError:
            await s.rollback(); return
    await update_trend(bot, mid)
