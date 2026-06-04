from __future__ import annotations
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.db.models import Match, Role, ForbiddenWord, MediaHash, SecurityLog, Setting, Suggestion, User, Prediction, Badge, Invitation
from app.keyboards import admin_panel, category_kb, close_match_kb
from app.services.common import is_admin, is_super, is_trusted, set_setting, get_setting, log
from app.services.matches import split_sides, publish_match, publish_trend, ranking_text, apply_result
from app.config import get_settings
settings=get_settings(); router=Router()

class MatchCreate(StatesGroup):
    category=State(); image=State(); title=State(); starts=State(); ends=State()
class RuleEdit(StatesGroup): text=State()
class WordAdd(StatesGroup): word=State()
class RoleEdit(StatesGroup): user_id=State()
class CloseState(StatesGroup): score=State()
class ClarifyState(StatesGroup): text=State()

async def guard_admin(c_or_m):
    uid=c_or_m.from_user.id
    async with SessionLocal() as session: return await is_admin(session,uid)

@router.message(F.text.in_(['/admin','/panel']))
async def panel(m:Message):
    async with SessionLocal() as session:
        if not await is_admin(session,m.from_user.id): return
        sup=await is_super(session,m.from_user.id)
    await m.answer('Panel admin', reply_markup=admin_panel(sup))

@router.callback_query(F.data.startswith('admin:'))
async def admin_router(c:CallbackQuery, state:FSMContext, bot:Bot):
    async with SessionLocal() as session:
        if not await is_admin(session,c.from_user.id): await c.answer('Accès refusé',show_alert=True); return
        sup=await is_super(session,c.from_user.id)
    action=c.data.split(':')[1]
    if action=='create_match':
        await state.set_state(MatchCreate.category); await c.message.answer('Choisis la catégorie', reply_markup=category_kb('admin_cat'))
    elif action=='active_matches':
        async with SessionLocal() as session:
            ms=(await session.execute(select(Match).where(Match.status.in_(['active','pending_result'])).order_by(Match.starts_at))).scalars().all()
        text='📋 Matchs en cours\n\n'+'\n'.join([f"#{m.id} {m.title} — {m.status}" for m in ms]) if ms else 'Aucun match en cours.'
        await c.message.answer(text)
        for m in ms: await c.message.answer(f'Clôture #{m.id}', reply_markup=close_match_kb(m.id,m.side_a,m.side_b))
    elif action=='closed_matches':
        async with SessionLocal() as session:
            ms=(await session.execute(select(Match).where(Match.status.in_(['closed','cancelled'])).order_by(Match.id.desc()).limit(20))).scalars().all()
        await c.message.answer('✅ Matchs clôturés\n\n'+'\n'.join([f"#{m.id} {m.title} — {m.winner or m.status} {m.final_score or ''}" for m in ms]) if ms else 'Aucun match clôturé.')
    elif action=='stats':
        async with SessionLocal() as session:
            users=(await session.execute(select(func.count(User.id)))).scalar() or 0
            matches=(await session.execute(select(func.count(Match.id)))).scalar() or 0
            preds=(await session.execute(select(func.count()).select_from(Prediction))).scalar() or 0
            rank=await ranking_text(session,5)
        await c.message.answer(f'📊 Statistiques\nUtilisateurs: {users}\nMatchs: {matches}\nPronostics: {preds}\n\n{rank}')
    elif action=='words':
        await state.set_state(WordAdd.word); await c.message.answer('Envoie un mot interdit à ajouter. Pour supprimer : -mot')
    elif action=='rules':
        await state.set_state(RuleEdit.text); await c.message.answer('Envoie le texte des règles qui tournera toutes les 2h.')
    elif action=='close_group':
        from aiogram.types import ChatPermissions
        await bot.set_chat_permissions(settings.GROUP_ID, ChatPermissions(can_send_messages=False, can_send_photos=False, can_send_videos=False, can_send_documents=False, can_send_audios=False, can_send_voice_notes=False, can_send_video_notes=False))
        await c.message.answer('🔒 Groupe fermé.');
    elif action=='open_group':
        from aiogram.types import ChatPermissions
        await bot.set_chat_permissions(settings.GROUP_ID, ChatPermissions(can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_documents=True, can_send_audios=True, can_send_voice_notes=True, can_send_video_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=False))
        await c.message.answer('🔓 Groupe ouvert.')
    elif action=='media_hashes':
        await c.message.answer('Envoie /ban en réponse à un média pour l’interdire définitivement. Le terme technique ne sera jamais affiché publiquement.')
    elif action=='info':
        db='✅ Connectée'
        try:
            async with SessionLocal() as session: await session.execute(select(func.count(Match.id)))
        except Exception as e: db=f'❌ {e}'
        send='✅ Fonctionnel'
        try:
            test=await bot.send_message(settings.GROUP_ID, 'test')
            await bot.delete_message(settings.GROUP_ID, test.message_id)
        except Exception as e: send=f'❌ {e}'
        await c.message.answer(f"📊 Info\n\nBot : ✅ En ligne\nBase de données : {db}\nRailway : ✅ Process lancé\nTâches planifiées : ✅ Actives\nEnvoi messages : {send}\nGroupe principal : {settings.GROUP_ID}\nVersion : {settings.APP_VERSION}")
    await c.answer()

@router.callback_query(F.data.startswith('admin_cat:'))
async def admin_cat(c:CallbackQuery,state:FSMContext):
    await state.update_data(category=c.data.split(':',1)[1]); await state.set_state(MatchCreate.image); await c.message.answer('Envoie l’image du match.'); await c.answer()
@router.message(MatchCreate.image, F.photo)
async def match_image(m:Message,state:FSMContext):
    await state.update_data(image=m.photo[-1].file_id); await state.set_state(MatchCreate.title); await m.answer('Entre le titre du match. Exemple : France 🇫🇷 vs Côte d’Ivoire 🇨🇮')
@router.message(MatchCreate.title)
async def match_title(m:Message,state:FSMContext):
    await state.update_data(title=m.text); await state.set_state(MatchCreate.starts); await m.answer('Date de début au format YYYY-MM-DD HH:MM, exemple 2026-06-15 20:00')
@router.message(MatchCreate.starts)
async def match_starts(m:Message,state:FSMContext):
    try: dt=datetime.strptime(m.text.strip(),'%Y-%m-%d %H:%M')
    except Exception: await m.answer('Format invalide. Exemple : 2026-06-15 20:00'); return
    await state.update_data(starts=dt); await state.set_state(MatchCreate.ends); await m.answer('Date de fin du match au format YYYY-MM-DD HH:MM')
@router.message(MatchCreate.ends)
async def match_ends(m:Message,state:FSMContext,bot:Bot):
    try: ends=datetime.strptime(m.text.strip(),'%Y-%m-%d %H:%M')
    except Exception: await m.answer('Format invalide. Exemple : 2026-06-15 22:00'); return
    data=await state.get_data(); a,b=split_sides(data['title'])
    async with SessionLocal() as session:
        match=Match(category=data['category'],title=data['title'],side_a=a,side_b=b,image_file_id=data['image'],starts_at=data['starts'],votes_close_at=data['starts'],ends_at=ends,created_by=m.from_user.id,status='active')
        session.add(match); await session.commit(); await session.refresh(match)
        await publish_match(bot,session,match); await publish_trend(bot,session,match)
    await m.answer(f'✅ Match créé et publié : #{match.id}'); await state.clear()

@router.message(RuleEdit.text)
async def rules_text(m:Message,state:FSMContext):
    async with SessionLocal() as session: await set_setting(session,'rules_text',m.text)
    await m.answer('✅ Règles enregistrées.'); await state.clear()
@router.message(WordAdd.word)
async def word_edit(m:Message,state:FSMContext):
    txt=(m.text or '').strip().lower()
    async with SessionLocal() as session:
        if txt.startswith('-'):
            obj=await session.get(ForbiddenWord,txt[1:]);
            if obj: await session.delete(obj); await session.commit(); await m.answer('✅ Mot supprimé.')
        else:
            session.add(ForbiddenWord(word=txt,created_by=m.from_user.id)); await session.commit(); await m.answer('✅ Mot ajouté.')
    await state.clear()

@router.callback_query(F.data.startswith('super:'))
async def super_router(c:CallbackQuery,state:FSMContext):
    async with SessionLocal() as session:
        if not await is_super(session,c.from_user.id): await c.answer('Super admin uniquement',show_alert=True); return
        action=c.data.split(':')[1]
        if action=='logs':
            logs=(await session.execute(select(SecurityLog).order_by(SecurityLog.id.desc()).limit(15))).scalars().all()
            text='📜 Logs sécurité\n\n'+'\n'.join([f'#{l.id} {l.event} user={l.user_id} chat={l.chat_id} — {l.details[:80]}' for l in logs]) if logs else 'Aucun log.'
            await c.message.answer(text); await c.answer(); return
        if action=='settings':
            await c.message.answer(f'⚙️ Paramètres\nPRONO_REPOST_MINUTES={settings.PRONO_REPOST_MINUTES}\nLEADERBOARD_HOURS={settings.LEADERBOARD_HOURS}\nRULES_HOURS={settings.RULES_HOURS}\nSHARE_HOURS={settings.SHARE_HOURS}\nSUGGESTION_HOURS={settings.SUGGESTION_HOURS}\nGROUP_ID={settings.GROUP_ID}')
            await c.answer(); return
    await state.update_data(role_action=action); await state.set_state(RoleEdit.user_id)
    await c.message.answer('Envoie le Telegram ID concerné.'); await c.answer()
@router.message(RoleEdit.user_id)
async def role_edit(m:Message,state:FSMContext):
    data=await state.get_data(); uid=int((m.text or '0').strip())
    mapping={'add_admin':'admin','remove_admin':'admin','add_trusted':'trusted','remove_trusted':'trusted'}
    role=mapping[data['role_action']]
    async with SessionLocal() as session:
        if data['role_action'].startswith('add'):
            if not await session.get(Role,{'user_id':uid,'role':role}): session.add(Role(user_id=uid,role=role))
            await session.commit(); await m.answer(f'✅ {role} ajouté : {uid}')
        else:
            obj=await session.get(Role,{'user_id':uid,'role':role})
            if obj: await session.delete(obj)
            await session.commit(); await m.answer(f'✅ {role} retiré : {uid}')
    await state.clear()

@router.callback_query(F.data.startswith('close:winner:'))
async def close_winner(c:CallbackQuery,state:FSMContext):
    _,_,mid,winner=c.data.split(':')
    if winner=='CANCEL':
        async with SessionLocal() as session: await apply_result(session,int(mid),'CANCEL',None)
        await c.message.answer('Match annulé.'); await c.answer(); return
    await state.update_data(close_mid=int(mid), close_winner=winner); await state.set_state(CloseState.score)
    await c.message.answer('Score exact final ? Exemple : 2-1'); await c.answer()
@router.message(CloseState.score)
async def close_score(m:Message,state:FSMContext):
    data=await state.get_data()
    async with SessionLocal() as session: mt=await apply_result(session,data['close_mid'],data['close_winner'],m.text.strip())
    await m.answer(f'✅ Résultat clôturé pour {mt.title}.'); await state.clear()

@router.callback_query(F.data.startswith('sugg:'))
async def sugg_admin(c:CallbackQuery, state:FSMContext):
    _,action,sid=c.data.split(':'); sid=int(sid)
    async with SessionLocal() as session:
        s=await session.get(Suggestion,sid)
        if not s:
            await c.answer('Suggestion introuvable', show_alert=True); return
        if action == 'clarify':
            await state.update_data(clarify_suggestion_id=sid)
            await state.set_state(ClarifyState.text)
            await c.message.answer(f'Envoie la question à transmettre à l’utilisateur pour la suggestion #{sid}.')
            await c.answer(); return
        s.status={'accept':'accepted','refuse':'refused'}[action]
        if action == 'accept':
            u=await session.get(User,s.user_id)
            if u:
                u.accepted_suggestions += 1
                if u.accepted_suggestions >= 5 and not await session.get(Badge, {'user_id':u.id,'badge':'🧠 Scout'}): session.add(Badge(user_id=u.id,badge='🧠 Scout'))
                if u.accepted_suggestions >= 25 and not await session.get(Badge, {'user_id':u.id,'badge':'🎖 Analyste'}): session.add(Badge(user_id=u.id,badge='🎖 Analyste'))
                if u.accepted_suggestions >= 50 and not await session.get(Badge, {'user_id':u.id,'badge':'👑 Recruteur Officiel'}): session.add(Badge(user_id=u.id,badge='👑 Recruteur Officiel'))
        await session.commit()
    await c.message.answer(f'Suggestion #{sid} : {action}'); await c.answer()


@router.message(ClarifyState.text)
async def clarify_suggestion_send(m:Message, state:FSMContext, bot:Bot):
    data = await state.get_data()
    sid = int(data.get('clarify_suggestion_id', 0))
    async with SessionLocal() as session:
        s = await session.get(Suggestion, sid)
        if not s:
            await m.answer('Suggestion introuvable.'); await state.clear(); return
        s.status = 'needs_precision'
        await session.commit()
        try:
            REPL
            await m.answer('✅ Demande de précision envoyée à l’utilisateur.')
        except Exception as e:
            await m.answer(f'⚠️ Impossible de contacter l’utilisateur: {e}')
    await state.clear()
