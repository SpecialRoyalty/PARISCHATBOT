from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.keyboards.common import category_kb, admin_panel, kb
from app.states import CreateMatch, SetRules, AddWord, CloseMatch
from app.utils.dates import parse_dt
from app.services.matches import create_match, active_matches, closed_matches, match_stats, close_match, pending_matches, get_match, delete_result_prompts
from app.services.settings import set_setting, DEFAULT_RULES, get_setting
from app.services.moderation import add_word, list_words, delete_word
from app.services.roles import is_admin
from app.handlers.votes import refresh_group_match
from app.config import settings
from app.db.session import SessionLocal
router=Router()

async def guard_admin(c:CallbackQuery):
    if not await is_admin(c.from_user.id): await c.answer('Accès refusé', show_alert=True); return False
    return True

@router.callback_query(F.data=='admin:create')
async def create_start(c:CallbackQuery, state:FSMContext):
    if not await guard_admin(c): return
    await state.set_state(CreateMatch.category); await c.message.edit_text('Choisis la catégorie :', reply_markup=category_kb('createcat')); await c.answer()
@router.callback_query(F.data.startswith('createcat:'))
async def create_cat(c:CallbackQuery, state:FSMContext):
    await state.update_data(category=c.data.split(':',1)[1]); await state.set_state(CreateMatch.photo); await c.message.edit_text('Envoie l’image du match.'); await c.answer()
@router.message(CreateMatch.photo, F.photo)
async def create_photo(m:Message, state:FSMContext):
    await state.update_data(photo=m.photo[-1].file_id); await state.set_state(CreateMatch.title); await m.answer('Titre du match ?\nExemple : France 🇫🇷 vs Côte d’Ivoire 🇨🇮')
@router.message(CreateMatch.title)
async def create_title(m:Message, state:FSMContext):
    await state.update_data(title=m.text); await state.set_state(CreateMatch.start); await m.answer('Date/heure de début ?\nFormat : 2026-06-15 21:00')
@router.message(CreateMatch.start)
async def create_start_dt(m:Message, state:FSMContext):
    try: dt=parse_dt(m.text)
    except ValueError as e: await m.answer(str(e)); return
    await state.update_data(start_at=dt.isoformat()); await state.set_state(CreateMatch.end); await m.answer('Date/heure de fin approximative ?\nFormat : 2026-06-15 22:00')
@router.message(CreateMatch.end)
async def create_end_dt(m:Message, state:FSMContext, bot):
    try: end=parse_dt(m.text)
    except ValueError as e: await m.answer(str(e)); return
    data=await state.get_data(); from datetime import datetime
    match=await create_match(data['category'],data['title'],data['photo'],datetime.fromisoformat(data['start_at']),end,m.from_user.id,'active')
    await state.clear(); await m.answer(f'✅ Match créé #{match.id}.', reply_markup=admin_panel())
    await refresh_group_match(bot, match.id)

@router.callback_query(F.data=='admin:active')
async def admin_active(c:CallbackQuery):
    if not await guard_admin(c): return
    rows=[]; text='📋 Matchs actifs\n\n'
    for m in await active_matches():
        st=await match_stats(m.id)
        text+=f"#{m.id} {m.title}\nStatut: {m.status}\nDébut: {m.start_at}\nFin: {m.end_at}\nVotes: {st['total']} | {m.team_a} {st['pa']}% | {m.team_b} {st['pb']}% | Nul {st['pd']}%\n\n"
        rows.append([(f'🏁 Clôturer #{m.id}', f'admin:close:{m.id}'),(f'🛑 Annuler #{m.id}', f'admin:cancel:{m.id}')])
    rows.append([('⬅ Retour','nav:admin')])
    await c.message.edit_text(text or 'Aucun match actif', reply_markup=kb(rows)); await c.answer()
@router.callback_query(F.data.startswith('admin:cancel:'))
async def cancel_match(c:CallbackQuery):
    mid=int(c.data.split(':')[-1]); from app.db.session import SessionLocal; from app.db.models import Match
    async with SessionLocal() as s:
        m=await s.get(Match,mid); m.status='cancelled'; await s.commit()
    await c.message.answer('Match annulé.'); await c.answer()
@router.callback_query(F.data.startswith('admin:close:'))
async def close_choose(c:CallbackQuery):
    mid=int(c.data.split(':')[-1]); m=await get_match(mid)
    from app.keyboards.matches import close_result_kb
    await c.message.answer(f'Clôture : {m.title}\nQui a gagné ?', reply_markup=close_result_kb(mid,m.team_a,m.team_b)); await c.answer()
@router.callback_query(F.data.startswith('close:'))
async def close_winner(c:CallbackQuery, state:FSMContext, bot):
    _,mid,winner=c.data.split(':')
    # Dès qu'un admin/trusted répond, on supprime la demande chez tous les autres.
    await delete_result_prompts(bot, int(mid))
    if winner=='cancel':
        await close_match(int(mid),'cancelled',None); await c.message.answer('Match annulé/clôturé.'); await c.answer(); return
    await state.update_data(close_mid=int(mid), close_winner=winner); await state.set_state(CloseMatch.score); await c.message.answer('Score exact ? Exemple : 2-1'); await c.answer()
@router.message(CloseMatch.score, F.chat.type=='private', F.text.regexp(r'^\d+\s*-\s*\d+$'))
async def close_score(m:Message, state:FSMContext, bot):
    data=await state.get_data()
    if not data.get('close_mid'): return
    await close_match(data['close_mid'],data['close_winner'],m.text.replace(' ','')); await delete_result_prompts(bot, data['close_mid']); await state.clear(); await m.answer('✅ Match clôturé, statistiques mises à jour.')

@router.callback_query(F.data=='admin:closed')
async def admin_closed(c:CallbackQuery):
    text='📁 Matchs clôturés\n\n'
    for m in await closed_matches():
        st=await match_stats(m.id)
        text+=f"#{m.id} {m.title}\nRésultat: {m.result_score or m.result_winner}\nParticipants: {st['total']}\n\n"
    await c.message.edit_text(text, reply_markup=admin_panel()); await c.answer()
@router.callback_query(F.data=='admin:words')
async def words_menu(c:CallbackQuery):
    await c.message.edit_text('🚫 Mots interdits', reply_markup=kb([[('➕ Ajouter','admin:word_add')],[('📋 Voir liste','admin:word_list')],[('❌ Supprimer','admin:word_del')],[('⬅ Retour','nav:admin')]])); await c.answer()
@router.callback_query(F.data=='admin:word_add')
async def word_add(c:CallbackQuery, state:FSMContext): await state.set_state(AddWord.word); await c.message.answer('Mot ou expression à ajouter :'); await c.answer()
@router.message(AddWord.word)
async def word_add_msg(m:Message, state:FSMContext):
    status=await add_word(m.text,m.from_user.id)
    await state.clear()
    if status=='empty': await m.answer('Mot vide, rien ajouté.')
    elif status=='exists': await m.answer('Ce mot existe déjà.')
    else: await m.answer('✅ Mot ajouté.')
@router.callback_query(F.data=='admin:word_list')
async def word_list(c:CallbackQuery):
    words=await list_words(); await c.message.answer('Mots interdits:\n'+'\n'.join(f'#{w.id} {w.word}' for w in words) if words else 'Aucun mot.'); await c.answer()
@router.callback_query(F.data=='admin:word_del')
async def word_del_help(c:CallbackQuery): await c.message.answer('Envoie : supprimer mot <id>'); await c.answer()
@router.message(F.text.startswith('supprimer mot '))
async def word_del_msg(m:Message): await delete_word(int(m.text.split()[-1])); await m.answer('✅ Supprimé si existant.')
@router.callback_query(F.data=='admin:rules')
async def rules_menu(c:CallbackQuery, state:FSMContext): await state.set_state(SetRules.text); await c.message.answer('Envoie le nouveau règlement :'); await c.answer()
@router.message(SetRules.text)
async def rules_save(m:Message, state:FSMContext): await set_setting('rules_text',m.text); await state.clear(); await m.answer('✅ Règlement sauvegardé.')
@router.callback_query(F.data=='admin:close_group')
async def close_group(c:CallbackQuery, bot):
    from aiogram.types import ChatPermissions
    await bot.set_chat_permissions(settings.GROUP_ID, ChatPermissions(can_send_messages=False)); await c.answer('Groupe fermé', show_alert=True)
@router.callback_query(F.data=='admin:open_group')
async def open_group(c:CallbackQuery, bot):
    from aiogram.types import ChatPermissions
    await bot.set_chat_permissions(settings.GROUP_ID, ChatPermissions(can_send_messages=True,can_send_photos=True,can_send_videos=True,can_send_documents=True)); await c.answer('Groupe ouvert', show_alert=True)

@router.callback_query(F.data=='admin:stats')
async def admin_stats(c:CallbackQuery):
    if not await guard_admin(c): return
    from sqlalchemy import select, func
    from app.db.models import Match, Prediction, User, Suggestion, ForbiddenWord
    async with SessionLocal() as s:
        matches=(await s.execute(select(func.count(Match.id)))).scalar() or 0
        active=(await s.execute(select(func.count(Match.id)).where(Match.status=='active'))).scalar() or 0
        locked=(await s.execute(select(func.count(Match.id)).where(Match.status=='locked'))).scalar() or 0
        closed=(await s.execute(select(func.count(Match.id)).where(Match.status=='closed'))).scalar() or 0
        preds=(await s.execute(select(func.count(Prediction.id)))).scalar() or 0
        users=(await s.execute(select(func.count(User.id)))).scalar() or 0
        sugg=(await s.execute(select(func.count(Suggestion.id)).where(Suggestion.status=='pending'))).scalar() or 0
        words=(await s.execute(select(func.count(ForbiddenWord.id)))).scalar() or 0
    await c.message.answer(f"📊 Statistiques globales\n\nUtilisateurs PV : {users}\nMatchs total : {matches}\nActifs : {active}\nVerrouillés : {locked}\nClôturés : {closed}\nPronostics enregistrés : {preds}\nSuggestions en attente : {sugg}\nMots interdits : {words}")
    await c.answer()

@router.callback_query(F.data=='admin:trusted_requests')
async def admin_trusted_requests(c:CallbackQuery):
    if not await guard_admin(c): return
    rows=[]; text='📨 Demandes Trusted\n\n'
    for m in await pending_matches():
        text+=f"#{m.id} {m.title}\nCatégorie: {m.category}\nDébut: {m.start_at}\nFin: {m.end_at}\nProposé par: {m.proposed_by}\n\n"
        rows.append([(f'✅ Valider #{m.id}', f'admin:approve_pending:{m.id}'),(f'❌ Refuser #{m.id}', f'admin:reject_pending:{m.id}')])
    if not rows: text+='Aucune demande en attente.'
    rows.append([('⬅ Retour','nav:admin')])
    await c.message.answer(text, reply_markup=kb(rows)); await c.answer()

@router.callback_query(F.data.startswith('admin:approve_pending:'))
async def approve_pending(c:CallbackQuery, bot):
    if not await guard_admin(c): return
    mid=int(c.data.split(':')[-1])
    from app.db.models import Match
    async with SessionLocal() as s:
        m=await s.get(Match, mid)
        if not m or m.status!='pending': await c.answer('Demande introuvable.', show_alert=True); return
        m.status='active'; m.created_by=c.from_user.id
        await s.commit()
    await refresh_group_match(bot, mid)
    await c.message.answer(f'✅ Demande #{mid} validée et publiée.'); await c.answer()

@router.callback_query(F.data.startswith('admin:reject_pending:'))
async def reject_pending(c:CallbackQuery):
    if not await guard_admin(c): return
    mid=int(c.data.split(':')[-1])
    from app.db.models import Match
    async with SessionLocal() as s:
        m=await s.get(Match, mid)
        if m and m.status=='pending': m.status='cancelled'; await s.commit()
    await c.message.answer(f'❌ Demande #{mid} refusée.'); await c.answer()

@router.callback_query(F.data=='admin:suggestions')
async def admin_suggestions(c:CallbackQuery):
    if not await guard_admin(c): return
    from sqlalchemy import select
    from app.db.models import Suggestion
    async with SessionLocal() as s:
        sugs=(await s.execute(select(Suggestion).where(Suggestion.status=='pending').order_by(Suggestion.id.desc()).limit(20))).scalars().all()
    rows=[]; text='💡 Suggestions utilisateurs\n\n'
    for sug in sugs:
        text+=f"#{sug.id} {sug.title}\nCatégorie: {sug.category}\nDate: {sug.proposed_date}\nUtilisateur: {sug.user_id}\n\n"
        rows.append([(f'✅ Accepter #{sug.id}', f'admin:accept_sug:{sug.id}'),(f'❌ Refuser #{sug.id}', f'admin:reject_sug:{sug.id}')])
    if not sugs: text+='Aucune suggestion en attente.'
    rows.append([('⬅ Retour','nav:admin')])
    await c.message.answer(text, reply_markup=kb(rows)); await c.answer()

@router.callback_query(F.data.startswith('admin:accept_sug:'))
async def accept_sug(c:CallbackQuery):
    if not await guard_admin(c): return
    sid=int(c.data.split(':')[-1])
    from app.db.models import Suggestion
    async with SessionLocal() as s:
        sug=await s.get(Suggestion,sid)
        if sug: sug.status='accepted'; await s.commit()
    await c.message.answer(f'✅ Suggestion #{sid} acceptée. Crée le match depuis “Créer match” si tu veux la publier.'); await c.answer()

@router.callback_query(F.data.startswith('admin:reject_sug:'))
async def reject_sug(c:CallbackQuery):
    if not await guard_admin(c): return
    sid=int(c.data.split(':')[-1])
    from app.db.models import Suggestion
    async with SessionLocal() as s:
        sug=await s.get(Suggestion,sid)
        if sug: sug.status='rejected'; await s.commit()
    await c.message.answer(f'❌ Suggestion #{sid} refusée.'); await c.answer()
