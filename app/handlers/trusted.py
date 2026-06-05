from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.services.roles import is_trusted, is_admin
from app.keyboards.common import category_kb, trusted_panel
from app.states import TrustedMatch, AddWord
from app.utils.dates import parse_dt
from app.services.matches import create_match
from app.services.moderation import add_word
from app.config import settings
from datetime import datetime
router=Router()

async def guard(c):
    if not await is_trusted(c.from_user.id): await c.answer('Accès refusé', show_alert=True); return False
    return True
@router.callback_query(F.data=='trusted:propose')
async def tr_prop(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.set_state(TrustedMatch.category); await c.message.edit_text('Catégorie :', reply_markup=category_kb('trcat')); await c.answer()
@router.callback_query(F.data.startswith('trcat:'))
async def tr_cat(c:CallbackQuery,state:FSMContext):
    await state.update_data(category=c.data.split(':',1)[1]); await state.set_state(TrustedMatch.photo); await c.message.answer('Envoie l’image du match.'); await c.answer()
@router.message(TrustedMatch.photo, F.photo)
async def tr_photo(m:Message,state:FSMContext): await state.update_data(photo=m.photo[-1].file_id); await state.set_state(TrustedMatch.title); await m.answer('Titre du match ?')
@router.message(TrustedMatch.title)
async def tr_title(m:Message,state:FSMContext): await state.update_data(title=m.text); await state.set_state(TrustedMatch.start); await m.answer('Début ? Format : 2026-06-15 21:00')
@router.message(TrustedMatch.start)
async def tr_start(m:Message,state:FSMContext):
    try: dt=parse_dt(m.text)
    except ValueError as e: await m.answer(str(e)); return
    await state.update_data(start_at=dt.isoformat()); await state.set_state(TrustedMatch.end); await m.answer('Fin approximative ? Format : 2026-06-15 22:00')
@router.message(TrustedMatch.end)
async def tr_end(m:Message,state:FSMContext,bot):
    try: end=parse_dt(m.text)
    except ValueError as e: await m.answer(str(e)); return
    d=await state.get_data()
    match=await create_match(d['category'],d['title'],d['photo'],datetime.fromisoformat(d['start_at']),end,None,'pending',m.from_user.id)
    await state.clear(); await m.answer('✅ Votre demande a été envoyée à la modération.', reply_markup=trusted_panel())
    from app.db.session import SessionLocal
    from app.db.models import Role
    from sqlalchemy import select
    async with SessionLocal() as s:
        ids=(await s.execute(select(Role.user_id).where(Role.role.in_(['admin','super_admin'])))).scalars().all()
    for uid in set(ids):
        try: await bot.send_message(uid,f'📨 Demande Trusted #{match.id}\n{match.title}\nCatégorie: {match.category}\nDébut: {match.start_at}\nFin: {match.end_at}\n\nValider depuis le panel admin.')
        except Exception: pass
@router.callback_query(F.data=='trusted:add_word')
async def tr_word(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.clear()
    await state.update_data(word_source='trusted')
    await state.set_state(AddWord.word)
    await c.message.answer('Mot ou expression à ajouter :')
    await c.answer()
@router.callback_query(F.data=='trusted:commands')
async def tr_commands(c:CallbackQuery): await c.message.answer('Commandes disponibles :\n/supprime\n/ban'); await c.answer()

@router.callback_query(F.data=='trusted:my_requests')
async def trusted_my_requests(c:CallbackQuery):
    if not await guard(c):
        return
    from sqlalchemy import select
    from app.db.models import Match
    from app.db.session import SessionLocal
    async with SessionLocal() as s:
        res = await s.execute(
            select(Match)
            .where(Match.proposed_by == c.from_user.id)
            .order_by(Match.id.desc())
            .limit(20)
        )
        matches = res.scalars().all()
    if not matches:
        await c.message.answer('📊 Mes propositions\n\nAucune proposition pour le moment.', reply_markup=trusted_panel())
        await c.answer()
        return
    status_map = {
        'pending': '🟡 En attente',
        'active': '🟢 Validée / publiée',
        'locked': '🔒 Votes fermés',
        'closed': '✅ Clôturée',
        'cancelled': '🔴 Refusée / annulée',
    }
    text = '📊 Mes propositions\n\n'
    for m in matches:
        text += f"#{m.id} {m.title}\nCatégorie : {m.category}\nStatut : {status_map.get(m.status, m.status)}\nDébut : {m.start_at}\nFin : {m.end_at or '—'}\n\n"
    await c.message.answer(text, reply_markup=trusted_panel())
    await c.answer()
