from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, delete
from datetime import datetime
from app.config import settings
from app.keyboards import admin_panel, close_result
from app.db.session import SessionLocal
from app.db.models import Match, ForbiddenWord, Prediction, User, Suggestion, SecurityLog
from app.utils.text import split_title
from app.services.core import publish_match, update_trend, set_setting, get_setting, send_leaderboard

router=Router()
admin_state: dict[int, dict] = {}

def is_admin(uid:int): return uid in settings.admin_ids
def is_super(uid:int): return uid in settings.super_admin_ids

@router.callback_query(F.data=='admin:create')
async def create(cb:CallbackQuery):
    if not is_admin(cb.from_user.id): return
    admin_state[cb.from_user.id]={'flow':'create','step':'category'}
    await cb.message.answer('Catégorie ? Foot / Basket / Tennis / Boxe / Autre')
    await cb.answer()

@router.message(lambda m: m.chat.type == 'private' and m.from_user and m.from_user.id in admin_state)
async def admin_text(message:Message, bot:Bot):
    st=admin_state.get(message.from_user.id)
    if not st or not is_admin(message.from_user.id): return
    if st.get('flow')=='result_score':
        mid=st['match_id']; winner=st['winner']; score=message.text.strip().replace(':','-')
        async with SessionLocal() as s:
            m=await s.get(Match,mid); m.status='closed'; m.result_winner=winner; m.result_score=score
            preds=(await s.execute(select(Prediction).where(Prediction.match_id==mid))).scalars().all()
            for p in preds:
                u=await s.get(User,p.user_id)
                ok=p.winner==winner; exact=ok and p.score==score
                p.is_correct=ok; p.exact=exact; u.total+=1
                if ok: u.correct+=1; u.streak+=1
                else: u.streak=0
                if exact: u.exact_scores+=1
            await s.commit()
        admin_state.pop(message.from_user.id,None)
        await message.answer('✅ Résultat enregistré et statistiques mises à jour.')
        await send_leaderboard(bot)
        return
    if st['flow']=='create':
        step=st['step']
        if step=='category': st['category']=message.text.strip(); st['step']='photo'; await message.answer('Envoie l’image du match.'); return
        if step=='photo':
            if message.photo: st['photo_file_id']=message.photo[-1].file_id; st['step']='title'; await message.answer('Titre du match ? Exemple : France 🇫🇷 vs Côte d’Ivoire 🇨🇮')
            else: await message.answer('Envoie une image.')
            return
        if step=='title': st['title']=message.text.strip(); st['step']='start'; await message.answer('Date/heure début votes fermés ? Format UTC : 2026-06-15 20:00'); return
        if step=='start':
            try: st['start_at']=datetime.strptime(message.text.strip(),'%Y-%m-%d %H:%M')
            except ValueError: await message.answer('Format invalide : 2026-06-15 20:00'); return
            st['step']='end'; await message.answer('Date/heure fin match approximative ? Format UTC : 2026-06-15 22:00'); return
        if step=='end':
            try: end=datetime.strptime(message.text.strip(),'%Y-%m-%d %H:%M')
            except ValueError: await message.answer('Format invalide.'); return
            a,b=split_title(st['title'])
            async with SessionLocal() as s:
                m=Match(category=st['category'], title=st['title'], option_a=a, option_b=b, photo_file_id=st.get('photo_file_id'), start_at=st['start_at'], vote_close_at=st['start_at'], end_at=end, created_by=message.from_user.id)
                s.add(m); await s.commit(); await s.refresh(m)
                mid=m.id
            admin_state.pop(message.from_user.id,None)
            async with SessionLocal() as s: m=await s.get(Match,mid)
            await publish_match(bot,m); await update_trend(bot,mid)
            await message.answer(f'✅ Match créé #{mid}')
    elif st['flow']=='rules':
        await set_setting('rules_text', message.text)
        admin_state.pop(message.from_user.id,None); await message.answer('✅ Règles enregistrées.')
    elif st['flow']=='welcome_text':
        await set_setting('welcome_text', message.text)
        admin_state.pop(message.from_user.id,None); await message.answer('✅ Message /start enregistré.')
    elif st['flow']=='welcome_photo':
        if message.photo:
            await set_setting('welcome_photo', message.photo[-1].file_id)
            admin_state.pop(message.from_user.id,None); await message.answer('✅ Photo /start enregistrée.')
        else: await message.answer('Envoie une photo.')
    elif st['flow']=='word_add':
        async with SessionLocal() as s:
            s.add(ForbiddenWord(word=message.text.lower().strip())); await s.commit()
        admin_state.pop(message.from_user.id,None); await message.answer('✅ Mot interdit ajouté.')

@router.callback_query(F.data=='admin:active')
async def active(cb:CallbackQuery):
    if not is_admin(cb.from_user.id): return
    async with SessionLocal() as s:
        ms=(await s.execute(select(Match).where(Match.status.in_(['active','locked'])).order_by(Match.start_at))).scalars().all()
    if not ms: await cb.message.answer('Aucun match actif/verrouillé.'); return
    for m in ms:
        await cb.message.answer(f'#{m.id} {m.title}\nStatut: {m.status}\nDébut: {m.start_at}', reply_markup=close_result(m) if m.status=='locked' else None)
    await cb.answer()

@router.callback_query(F.data.startswith('result:'))
async def result_pick(cb:CallbackQuery):
    if not is_admin(cb.from_user.id): return
    _, mid, winner=cb.data.split(':'); mid=int(mid)
    if winner=='cancel':
        async with SessionLocal() as s:
            m=await s.get(Match,mid); m.status='cancelled'; await s.commit()
        await cb.message.answer('🚫 Match annulé.'); return
    admin_state[cb.from_user.id]={'flow':'result_score','match_id':mid,'winner':winner}
    await cb.message.answer('Score exact final ? Exemple : 2-1')
    await cb.answer()

@router.message(lambda m: m.chat.type == 'private' and m.from_user and m.from_user.id in admin_state and admin_state.get(m.from_user.id, {}).get('flow') == 'result_score')
async def result_score(message:Message, bot:Bot):
    st=admin_state.get(message.from_user.id)
    if not st or st.get('flow')!='result_score': return
    mid=st['match_id']; winner=st['winner']; score=message.text.strip().replace(':','-')
    async with SessionLocal() as s:
        m=await s.get(Match,mid); m.status='closed'; m.result_winner=winner; m.result_score=score
        preds=(await s.execute(select(Prediction).where(Prediction.match_id==mid))).scalars().all()
        for p in preds:
            u=await s.get(User,p.user_id)
            ok=p.winner==winner; exact=ok and p.score==score
            p.is_correct=ok; p.exact=exact; u.total+=1
            if ok: u.correct+=1; u.streak+=1
            else: u.streak=0
            if exact: u.exact_scores+=1
        await s.commit()
    admin_state.pop(message.from_user.id,None)
    await message.answer('✅ Résultat enregistré et statistiques mises à jour.')
    await send_leaderboard(bot)

@router.callback_query(F.data=='admin:rules')
async def rules(cb:CallbackQuery):
    if not is_admin(cb.from_user.id): return
    admin_state[cb.from_user.id]={'flow':'rules'}
    await cb.message.answer('Envoie le texte complet des règles.'); await cb.answer()

@router.callback_query(F.data=='admin:words')
async def words(cb:CallbackQuery):
    if not is_admin(cb.from_user.id): return
    admin_state[cb.from_user.id]={'flow':'word_add'}
    await cb.message.answer('Envoie un mot interdit à ajouter.'); await cb.answer()

@router.callback_query(F.data=='admin:close_group')
async def close_group(cb:CallbackQuery, bot:Bot):
    if not is_admin(cb.from_user.id): return
    await bot.set_chat_permissions(settings.GROUP_ID, permissions={'can_send_messages':False})
    await cb.message.answer('🔒 Groupe fermé.'); await cb.answer()

@router.callback_query(F.data=='admin:open_group')
async def open_group(cb:CallbackQuery, bot:Bot):
    if not is_admin(cb.from_user.id): return
    await bot.set_chat_permissions(settings.GROUP_ID, permissions={'can_send_messages':True,'can_send_photos':True,'can_send_videos':True,'can_send_other_messages':True})
    await cb.message.answer('🔓 Groupe ouvert.'); await cb.answer()

@router.callback_query(F.data=='admin:info')
async def info(cb:CallbackQuery, bot:Bot):
    if not is_admin(cb.from_user.id): return
    db='✅'
    try:
        async with SessionLocal() as s: await s.execute(select(User).limit(1))
    except Exception: db='❌'
    msgok='✅'
    try: await bot.get_chat(settings.GROUP_ID)
    except Exception: msgok='❌'
    await cb.message.answer(f'ℹ️ Diagnostic\nBot : ✅\nBase de données : {db}\nGroupe principal : {msgok}\nMessages : {msgok}\nVersion : clean-final')
    await cb.answer()

@router.callback_query(F.data=='admin:startcfg')
async def startcfg(cb:CallbackQuery):
    if not is_super(cb.from_user.id): return
    admin_state[cb.from_user.id]={'flow':'welcome_text'}
    await cb.message.answer('Envoie le texte de bienvenue /start. Pour la photo, clique ensuite de nouveau et envoie une photo avec commande interne non nécessaire dans cette version.')
    await cb.answer()

@router.callback_query(F.data=='admin:logs')
async def logs(cb:CallbackQuery):
    if not is_super(cb.from_user.id): return
    async with SessionLocal() as s:
        rows=(await s.execute(select(SecurityLog).order_by(SecurityLog.created_at.desc()).limit(10))).scalars().all()
    await cb.message.answer('\n'.join([f'{r.created_at} {r.action} {r.details or ""}' for r in rows]) or 'Aucun log')
    await cb.answer()

@router.callback_query(F.data=='admin:roles')
async def roles(cb:CallbackQuery):
    if not is_super(cb.from_user.id): return
    await cb.message.answer('Rôles actuels chargés depuis variables Railway : SUPER_ADMIN_IDS, ADMIN_IDS, TRUSTED_IDS. Pour sécurité production, modifie-les dans Railway puis redéploie.')
    await cb.answer()
