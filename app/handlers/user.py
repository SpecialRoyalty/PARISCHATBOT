from __future__ import annotations
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.db.models import Match, Prediction, Suggestion, User
from app.keyboards import active_matches_kb, choice_kb, score_skip_kb, category_kb, admin_panel
from app.services.common import upsert_user, SCORE_RE, is_admin, is_super, get_setting
from app.services.matches import active_matches
from app.config import get_settings
settings=get_settings(); router=Router()

class VoteState(StatesGroup):
    score=State()
class SuggestState(StatesGroup):
    category=State(); title=State(); date=State(); image=State()

async def send_vote_private(bot: Bot, user_id: int, match_id: int) -> tuple[bool, str]:
    async with SessionLocal() as session:
        m = await session.get(Match, match_id)
        if not m or m.status != 'active' or m.starts_at <= datetime.utcnow():
            return False, 'Pronostic fermé.'
        exists = (await session.execute(select(Prediction).where(Prediction.match_id == match_id, Prediction.user_id == user_id))).scalar_one_or_none()
        if exists:
            return False, 'Tu as déjà pronostiqué pour ce match.'
        text = f"Qui va gagner d’après vous ?\n\n{m.title}"
        if m.image_file_id:
            await bot.send_photo(user_id, m.image_file_id, caption=text, reply_markup=choice_kb(m.id, m.side_a, m.side_b))
        else:
            await bot.send_message(user_id, text, reply_markup=choice_kb(m.id, m.side_a, m.side_b))
        return True, 'Pronostic envoyé.'

@router.message(F.text.startswith('/start'))
async def start(message:Message, bot:Bot):
    async with SessionLocal() as session:
        existing = await session.get(User, message.from_user.id)
        first_start = existing is None
        await upsert_user(session, message.from_user, bot)
        matches = await active_matches(session)
        admin = await is_admin(session, message.from_user.id)
        sup = await is_super(session, message.from_user.id)
        welcome_text = await get_setting(session, 'start_welcome_text', '')
        welcome_photo = await get_setting(session, 'start_welcome_photo', '')

    if admin:
        title = '👑 Panel Super Admin' if sup else '🛡 Panel Admin'
        await message.answer(f'{title}\nTon ID est bien reconnu : {message.from_user.id}', reply_markup=admin_panel(sup))

    if first_start and not admin and (welcome_text or welcome_photo):
        try:
            if welcome_photo:
                await bot.send_photo(message.from_user.id, welcome_photo, caption=welcome_text or 'Bienvenue 👋')
            else:
                await message.answer(welcome_text)
        except Exception:
            pass

    await message.answer('Voici les pronostics en cours. Tu peux ouvrir un match et donner ton avis.', reply_markup=active_matches_kb(matches))

@router.callback_query(F.data.startswith('vote:start:'))
async def vote_start(c:CallbackQuery, bot:Bot):
    mid=int(c.data.split(':')[-1])
    async with SessionLocal() as session:
        await upsert_user(session,c.from_user,bot)
    try:
        ok, info = await send_vote_private(bot, c.from_user.id, mid)
        await c.answer(info, show_alert=not ok)
    except Exception:
        try:
            me = await bot.me()
            await c.answer('Ouvre la conversation privée avec le bot pour voter.', url=f'https://t.me/{me.username}?start=vote_{mid}')
        except Exception:
            await c.answer('Ouvre la conversation privée avec le bot pour voter.', show_alert=True)

@router.callback_query(F.data.startswith('vote:choice:'))
async def vote_choice(c:CallbackQuery, state:FSMContext):
    _,_,mid,choice=c.data.split(':')
    await state.update_data(match_id=int(mid), choice=choice)
    await state.set_state(VoteState.score)
    await c.message.answer('Prédire le score exact ?\nFormat : 2-1', reply_markup=score_skip_kb(int(mid)))
    await c.answer()

@router.callback_query(F.data.startswith('vote:score_skip:'))
async def score_skip(c:CallbackQuery, state:FSMContext):
    data=await state.get_data(); mid=int(c.data.split(':')[-1])
    await save_prediction(c.from_user.id, mid, data.get('choice'), None, c.message)
    await state.clear(); await c.answer()

@router.message(VoteState.score)
async def score_entered(message:Message, state:FSMContext):
    if not SCORE_RE.match(message.text or ''):
        await message.answer('Format invalide. Exemple : 2-1 ou clique sur Je ne sais pas.'); return
    data=await state.get_data()
    await save_prediction(message.from_user.id, data['match_id'], data['choice'], message.text.replace(':','-').replace(' ',''), message)
    await state.clear()

async def save_prediction(user_id:int, match_id:int, choice:str, score:str|None, target):
    async with SessionLocal() as session:
        m=await session.get(Match,match_id)
        if not m or m.status!='active' or m.starts_at <= datetime.utcnow():
            await target.answer('⛔ Les pronostics sont fermés.'); return
        session.add(Prediction(match_id=match_id,user_id=user_id,choice=choice,exact_score=score))
        try:
            await session.commit(); await target.answer('✅ Pronostic enregistré. Tu ne peux voter qu’une seule fois pour ce match.')
        except IntegrityError:
            await session.rollback(); await target.answer('Tu as déjà pronostiqué pour ce match.')

@router.callback_query(F.data == 'suggest:start')
async def suggest_start(c:CallbackQuery, state:FSMContext):
    await state.set_state(SuggestState.category)
    await c.message.answer('Choisis la catégorie :', reply_markup=category_kb('suggest_cat'))
    await c.answer()

@router.callback_query(F.data.startswith('suggest_cat:'))
async def suggest_cat(c:CallbackQuery, state:FSMContext):
    await state.update_data(category=c.data.split(':',1)[1]); await state.set_state(SuggestState.title)
    await c.message.answer('Entre le titre du match. Exemple : France 🇫🇷 vs Côte d’Ivoire 🇨🇮'); await c.answer()

@router.message(SuggestState.title)
async def suggest_title(m:Message,state:FSMContext):
    await state.update_data(title=m.text); await state.set_state(SuggestState.date); await m.answer('Date/heure si connue, sinon écris : inconnue')
@router.message(SuggestState.date)
async def suggest_date(m:Message,state:FSMContext):
    await state.update_data(date=m.text); await state.set_state(SuggestState.image); await m.answer('Envoie une image optionnelle, ou écris : non')
@router.message(SuggestState.image)
async def suggest_image(m:Message,state:FSMContext, bot:Bot):
    data=await state.get_data(); image=m.photo[-1].file_id if m.photo else None
    async with SessionLocal() as session:
        s=Suggestion(user_id=m.from_user.id,category=data['category'],title=data['title'],proposed_date=data['date'],image_file_id=image); session.add(s); await session.commit(); sid=s.id
    from app.keyboards import suggestion_admin_kb
    for aid in settings.admin_ids:
        try: await bot.send_message(aid, f"Nouvelle suggestion de match\nCatégorie : {data['category']}\nMatch : {data['title']}\nDate : {data['date']}", reply_markup=suggestion_admin_kb(sid))
        except Exception: pass
    await m.answer('✅ Suggestion envoyée à la modération.'); await state.clear()
