from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from app.keyboards.common import category_kb, user_panel
from app.services.settings import get_setting, DEFAULT_RULES
from app.services.users import upsert_user
from app.db.session import SessionLocal
from app.db.models import User, Suggestion, InviteLink
from app.states import SuggestMatch
from app.config import settings
router=Router()

@router.callback_query(F.data=='user:rules')
async def rules(c:CallbackQuery): await c.message.answer(await get_setting('rules_text', DEFAULT_RULES)); await c.answer()
@router.callback_query(F.data=='user:share')
async def share(c:CallbackQuery, bot):
    async with SessionLocal() as s:
        link=(await s.execute(select(InviteLink).where(InviteLink.user_id==c.from_user.id))).scalar_one_or_none()
        if not link:
            invite=await bot.create_chat_invite_link(settings.GROUP_ID, name=f'user_{c.from_user.id}', creates_join_request=False)
            link=InviteLink(user_id=c.from_user.id, link=invite.invite_link); s.add(link); await s.commit()
    await c.message.answer(f'📢 Voici ton lien personnel :\n{link.link}')
    await c.answer()
@router.callback_query(F.data=='user:suggest')
async def suggest(c:CallbackQuery,state:FSMContext): await state.set_state(SuggestMatch.category); await c.message.edit_text('Choisissez une catégorie :', reply_markup=category_kb('sugcat')); await c.answer()
@router.callback_query(F.data.startswith('sugcat:'))
async def sug_cat(c:CallbackQuery,state:FSMContext): await state.update_data(category=c.data.split(':',1)[1]); await state.set_state(SuggestMatch.title); await c.message.answer('Titre du match ?'); await c.answer()
@router.message(SuggestMatch.title)
async def sug_title(m:Message,state:FSMContext): await state.update_data(title=m.text); await state.set_state(SuggestMatch.date); await m.answer('Date si connue ? Sinon écris : inconnue')
@router.message(SuggestMatch.date)
async def sug_date(m:Message,state:FSMContext): await state.update_data(date=m.text); await state.set_state(SuggestMatch.photo); await m.answer('Image optionnelle : envoie une photo ou écris passer.')
@router.message(SuggestMatch.photo)
async def sug_photo(m:Message,state:FSMContext,bot):
    d=await state.get_data(); photo=m.photo[-1].file_id if m.photo else None
    async with SessionLocal() as s:
        sug=Suggestion(user_id=m.from_user.id, category=d['category'], title=d['title'], proposed_date=d['date'], photo_file_id=photo); s.add(sug); await s.commit(); await s.refresh(sug)
    await state.clear(); await m.answer('✅ Suggestion envoyée à la modération.', reply_markup=user_panel())
    from app.db.models import Role
    async with SessionLocal() as s:
        ids=(await s.execute(select(Role.user_id).where(Role.role.in_(['admin','super_admin'])))).scalars().all()
    for uid in set(ids):
        try: await bot.send_message(uid,f'💡 Nouvelle suggestion #{sug.id}\nCatégorie: {sug.category}\nMatch: {sug.title}\nDate: {sug.proposed_date}')
        except Exception: pass
@router.callback_query(F.data=='user:leaderboard')
async def leaderboard(c:CallbackQuery):
    async with SessionLocal() as s:
        users=(await s.execute(select(User).where(User.total_predictions>=10).order_by((User.good_predictions*1.0/User.total_predictions).desc(), User.total_predictions.desc()).limit(10))).scalars().all()
    lines=['🏆 TOP PRONOSTIQUEURS\n']
    for i,u in enumerate(users,1):
        pct=round(u.good_predictions*100/u.total_predictions) if u.total_predictions else 0
        name=u.first_name or u.username or 'Membre'
        from app.utils.text import anonymize
        lines.append(f'{i}. {anonymize(name)} — {pct}% | {u.total_predictions} participations | 🎯 {u.exact_scores}')
    await c.message.answer('\n'.join(lines) if len(lines)>1 else 'Pas encore assez de participations.'); await c.answer()
@router.callback_query(F.data=='user:stats')
async def my_stats(c:CallbackQuery):
    async with SessionLocal() as s: u=await s.get(User,c.from_user.id)
    pct=round(u.good_predictions*100/u.total_predictions) if u and u.total_predictions else 0
    await c.message.answer(f'📈 Tes stats\n\nRéussite : {pct}%\nParticipations : {u.total_predictions if u else 0}\nScores exacts : {u.exact_scores if u else 0}\nInvitations : {u.invite_count if u else 0}'); await c.answer()
@router.callback_query(F.data=='user:badges')
async def badges(c:CallbackQuery):
    async with SessionLocal() as s: u=await s.get(User,c.from_user.id)
    b=[]
    if u:
        pct=(u.good_predictions/u.total_predictions) if u.total_predictions else 0
        if u.total_predictions>=25: b.append('💬 Actif')
        if u.total_predictions>=100: b.append('📈 Régulier')
        if u.total_predictions>=500: b.append('🚀 Vétéran')
        if u.exact_scores>=10: b.append('🎯 Tireur d’élite')
        if u.current_streak>=10: b.append('🔥 En feu')
        if u.current_streak>=20: b.append('⚡ Série légendaire')
        if pct>=0.75 and u.total_predictions>=100: b.append('🏆 Expert Sport')
        if pct>=0.80 and u.total_predictions>=250: b.append('👑 Légende')
    await c.message.answer('🎖 Tes badges\n\n' + ('\n'.join(b) if b else 'Aucun badge pour le moment.')); await c.answer()
