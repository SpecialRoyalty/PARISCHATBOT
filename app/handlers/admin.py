from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, delete
from datetime import datetime
from io import BytesIO
import hashlib

from app.config import settings
from app.keyboards import (
    admin_panel, close_result, category_keyboard, words_menu, word_delete_keyboard,
    media_menu, media_delete_keyboard, start_config_menu
)
from app.db.session import SessionLocal
from app.db.models import Match, ForbiddenWord, Prediction, User, SecurityLog, MediaHash
from app.utils.text import split_title
from app.services.core import publish_match, update_trend, set_setting, get_setting, send_leaderboard, log

router = Router()
admin_state: dict[int, dict] = {}


def is_admin(uid:int) -> bool:
    return uid in settings.admin_ids


def is_super(uid:int) -> bool:
    return uid in settings.super_admin_ids


async def media_hash_from_message(message: Message, bot: Bot) -> tuple[str, str] | None:
    file_id = None
    media_type = None
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    elif message.document:
        file_id = message.document.file_id
        media_type = 'document'
    if not file_id:
        return None
    f = await bot.get_file(file_id)
    bio = BytesIO()
    await bot.download_file(f.file_path, bio)
    data = bio.getvalue()
    if media_type == 'video':
        data = data[:1024 * 1024]
    return hashlib.sha256(data).hexdigest(), media_type


@router.callback_query(F.data == 'admin:panel')
async def panel(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    await cb.message.answer('✅ Panel admin', reply_markup=admin_panel(is_super(cb.from_user.id)))
    await cb.answer()


@router.callback_query(F.data == 'admin:create')
async def create(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    admin_state[cb.from_user.id] = {'flow': 'create', 'step': 'category'}
    await cb.message.answer('Choisis la catégorie du pronostic :', reply_markup=category_keyboard('createcat'))
    await cb.answer()


@router.callback_query(F.data.startswith('createcat:'))
async def create_category(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    st = admin_state.get(cb.from_user.id)
    if not st or st.get('flow') != 'create':
        admin_state[cb.from_user.id] = {'flow': 'create'}
        st = admin_state[cb.from_user.id]
    st['category'] = cb.data.split(':', 1)[1]
    st['step'] = 'photo'
    await cb.message.answer(f'✅ Catégorie : {st["category"]}\nEnvoie maintenant l’image du match.')
    await cb.answer()


@router.message(lambda m: m.chat.type == 'private' and m.from_user and m.from_user.id in admin_state)
async def admin_text(message: Message, bot: Bot):
    st = admin_state.get(message.from_user.id)
    if not st or not is_admin(message.from_user.id):
        return

    flow = st.get('flow')

    if flow == 'result_score':
        mid = st['match_id']; winner = st['winner']; score = (message.text or '').strip().replace(':','-')
        async with SessionLocal() as s:
            m = await s.get(Match, mid)
            if not m:
                await message.answer('Match introuvable.'); return
            m.status = 'closed'; m.result_winner = winner; m.result_score = score
            preds = (await s.execute(select(Prediction).where(Prediction.match_id == mid))).scalars().all()
            for p in preds:
                u = await s.get(User, p.user_id)
                if not u:
                    continue
                ok = p.winner == winner
                exact = ok and p.score == score
                p.is_correct = ok; p.exact = exact; u.total += 1
                if ok:
                    u.correct += 1; u.streak += 1
                else:
                    u.streak = 0
                if exact:
                    u.exact_scores += 1
            await s.commit()
        admin_state.pop(message.from_user.id, None)
        await message.answer('✅ Résultat enregistré et statistiques mises à jour.')
        await send_leaderboard(bot)
        return

    if flow == 'create':
        step = st.get('step')
        if step == 'category':
            await message.answer('Utilise les boutons pour choisir la catégorie.', reply_markup=category_keyboard('createcat'))
            return
        if step == 'photo':
            if message.photo:
                st['photo_file_id'] = message.photo[-1].file_id
                st['step'] = 'title'
                await message.answer('Titre du match ?\nExemple : France 🇫🇷 vs Côte d’Ivoire 🇨🇮')
            else:
                await message.answer('Envoie une image du match.')
            return
        if step == 'title':
            st['title'] = (message.text or '').strip()
            st['step'] = 'start'
            await message.answer('Date/heure de début et fermeture des votes ?\nFormat UTC : 2026-06-15 20:00')
            return
        if step == 'start':
            try:
                st['start_at'] = datetime.strptime((message.text or '').strip(), '%Y-%m-%d %H:%M')
            except ValueError:
                await message.answer('Format invalide. Exemple : 2026-06-15 20:00')
                return
            st['step'] = 'end'
            await message.answer('Date/heure de fin approximative du match ?\nFormat UTC : 2026-06-15 22:00')
            return
        if step == 'end':
            try:
                end = datetime.strptime((message.text or '').strip(), '%Y-%m-%d %H:%M')
            except ValueError:
                await message.answer('Format invalide. Exemple : 2026-06-15 22:00')
                return
            a, b = split_title(st['title'])
            async with SessionLocal() as s:
                m = Match(category=st['category'], title=st['title'], option_a=a, option_b=b,
                          photo_file_id=st.get('photo_file_id'), start_at=st['start_at'],
                          vote_close_at=st['start_at'], end_at=end, created_by=message.from_user.id)
                s.add(m); await s.commit(); await s.refresh(m)
                mid = m.id
            admin_state.pop(message.from_user.id, None)
            async with SessionLocal() as s:
                m = await s.get(Match, mid)
            await publish_match(bot, m)
            await update_trend(bot, mid)
            await message.answer(f'✅ Match créé #{mid}')
            return

    if flow == 'rules':
        await set_setting('rules_text', message.text or '')
        admin_state.pop(message.from_user.id, None)
        await message.answer('✅ Règles enregistrées.')
        return

    if flow == 'welcome_text':
        await set_setting('welcome_text', message.text or '')
        admin_state.pop(message.from_user.id, None)
        await message.answer('✅ Message /start enregistré.', reply_markup=start_config_menu())
        return

    if flow == 'welcome_photo':
        if message.photo:
            await set_setting('welcome_photo', message.photo[-1].file_id)
            admin_state.pop(message.from_user.id, None)
            await message.answer('✅ Photo /start enregistrée.', reply_markup=start_config_menu())
        else:
            await message.answer('Envoie une photo pour l’accueil /start.')
        return

    if flow == 'word_add':
        word = (message.text or '').lower().strip()
        if not word:
            await message.answer('Mot invalide.'); return
        async with SessionLocal() as s:
            if not await s.get(ForbiddenWord, word):
                s.add(ForbiddenWord(word=word))
                await s.commit()
        admin_state.pop(message.from_user.id, None)
        await message.answer(f'✅ Mot interdit ajouté : {word}', reply_markup=words_menu())
        return

    if flow == 'media_add':
        mh = await media_hash_from_message(message, bot)
        if not mh:
            await message.answer('Envoie une image, une vidéo ou un document média à interdire.')
            return
        h, t = mh
        async with SessionLocal() as s:
            if not await s.get(MediaHash, h):
                s.add(MediaHash(hash=h, media_type=t, added_by=message.from_user.id))
                await s.commit()
        admin_state.pop(message.from_user.id, None)
        await message.answer(f'✅ Média interdit ajouté.\nType : {t}\nHash : {h[:16]}…', reply_markup=media_menu())
        await log('media_hash_added_panel', f'{t}:{h}', message.from_user.id)
        return


@router.callback_query(F.data == 'admin:active')
async def active(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    async with SessionLocal() as s:
        ms = (await s.execute(select(Match).where(Match.status.in_(['active','locked'])).order_by(Match.start_at))).scalars().all()
    if not ms:
        await cb.message.answer('Aucun match actif/verrouillé.'); await cb.answer(); return
    for m in ms:
        await cb.message.answer(f'#{m.id} {m.title}\nStatut: {m.status}\nDébut: {m.start_at}', reply_markup=close_result(m) if m.status=='locked' else None)
    await cb.answer()


@router.callback_query(F.data == 'admin:closed')
async def closed(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    async with SessionLocal() as s:
        ms = (await s.execute(select(Match).where(Match.status.in_(['closed','cancelled'])).order_by(Match.start_at.desc()).limit(20))).scalars().all()
    if not ms:
        await cb.message.answer('Aucun match clôturé.'); await cb.answer(); return
    await cb.message.answer('\n\n'.join([f'#{m.id} {m.title}\nStatut: {m.status}\nRésultat: {m.result_winner or "-"} {m.result_score or ""}' for m in ms]))
    await cb.answer()


@router.callback_query(F.data.startswith('result:'))
async def result_pick(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    _, mid, winner = cb.data.split(':'); mid = int(mid)
    if winner == 'cancel':
        async with SessionLocal() as s:
            m = await s.get(Match, mid)
            if m: m.status = 'cancelled'; await s.commit()
        await cb.message.answer('🚫 Match annulé.'); await cb.answer(); return
    admin_state[cb.from_user.id] = {'flow':'result_score','match_id':mid,'winner':winner}
    await cb.message.answer('Score exact final ? Exemple : 2-1')
    await cb.answer()


@router.callback_query(F.data == 'admin:rules')
async def rules(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    admin_state[cb.from_user.id] = {'flow':'rules'}
    await cb.message.answer('Envoie le texte complet des règles. Il remplacera le texte actuel.')
    await cb.answer()


@router.callback_query(F.data == 'admin:words')
async def words(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    await cb.message.answer('Gestion des mots interdits :', reply_markup=words_menu())
    await cb.answer()


@router.callback_query(F.data == 'words:add')
async def words_add(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    admin_state[cb.from_user.id] = {'flow':'word_add'}
    await cb.message.answer('Envoie le mot interdit à ajouter.')
    await cb.answer()


@router.callback_query(F.data == 'words:list')
async def words_list(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    async with SessionLocal() as s:
        words = (await s.execute(select(ForbiddenWord).order_by(ForbiddenWord.word))).scalars().all()
    txt = '📋 Mots interdits :\n' + ('\n'.join([f'• {w.word}' for w in words]) if words else 'Aucun mot interdit.')
    await cb.message.answer(txt, reply_markup=words_menu())
    await cb.answer()


@router.callback_query(F.data == 'words:delete')
async def words_delete(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    async with SessionLocal() as s:
        words = (await s.execute(select(ForbiddenWord).order_by(ForbiddenWord.word))).scalars().all()
    if not words:
        await cb.message.answer('Aucun mot à supprimer.', reply_markup=words_menu())
    else:
        await cb.message.answer('Choisis le mot à supprimer :', reply_markup=word_delete_keyboard(words))
    await cb.answer()


@router.callback_query(F.data.startswith('worddel:'))
async def word_delete(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    word = cb.data.split(':',1)[1]
    async with SessionLocal() as s:
        await s.execute(delete(ForbiddenWord).where(ForbiddenWord.word == word))
        await s.commit()
    await cb.message.answer(f'🗑 Mot supprimé : {word}', reply_markup=words_menu())
    await cb.answer()


@router.callback_query(F.data == 'admin:media')
async def media(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    await cb.message.answer('Gestion des médias interdits par hash réel :', reply_markup=media_menu())
    await cb.answer()


@router.callback_query(F.data == 'media:add')
async def media_add(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    admin_state[cb.from_user.id] = {'flow':'media_add'}
    await cb.message.answer('Envoie le média à interdire.\nImage : hash SHA-256 complet.\nVidéo : hash SHA-256 du premier segment.')
    await cb.answer()


@router.callback_query(F.data == 'media:list')
async def media_list(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    async with SessionLocal() as s:
        items = (await s.execute(select(MediaHash).order_by(MediaHash.created_at.desc()).limit(30))).scalars().all()
    txt = '📋 Médias interdits :\n' + ('\n'.join([f'• {i.media_type} {i.hash[:16]}…' for i in items]) if items else 'Aucun média interdit.')
    await cb.message.answer(txt, reply_markup=media_menu())
    await cb.answer()


@router.callback_query(F.data == 'media:delete')
async def media_delete_menu(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    async with SessionLocal() as s:
        items = (await s.execute(select(MediaHash).order_by(MediaHash.created_at.desc()).limit(30))).scalars().all()
    if not items:
        await cb.message.answer('Aucun hash à supprimer.', reply_markup=media_menu())
    else:
        await cb.message.answer('Choisis le hash à supprimer :', reply_markup=media_delete_keyboard(items))
    await cb.answer()


@router.callback_query(F.data.startswith('mediadelp:'))
async def media_delete(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    prefix = cb.data.split(':',1)[1]
    async with SessionLocal() as s:
        items = (await s.execute(select(MediaHash).where(MediaHash.hash.startswith(prefix)))).scalars().all()
        for item in items:
            await s.delete(item)
        await s.commit()
    await cb.message.answer(f'🗑 Hash supprimé : {prefix}…', reply_markup=media_menu())
    await cb.answer()


@router.callback_query(F.data == 'admin:close_group')
async def close_group(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id): return
    await bot.set_chat_permissions(settings.GROUP_ID, permissions={'can_send_messages':False})
    await cb.message.answer('🔒 Groupe fermé.'); await cb.answer()


@router.callback_query(F.data == 'admin:open_group')
async def open_group(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id): return
    await bot.set_chat_permissions(settings.GROUP_ID, permissions={'can_send_messages':True,'can_send_photos':True,'can_send_videos':True,'can_send_other_messages':True})
    await cb.message.answer('🔓 Groupe ouvert.'); await cb.answer()


@router.callback_query(F.data == 'admin:info')
async def info(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id): return
    db='✅'
    try:
        async with SessionLocal() as s: await s.execute(select(User).limit(1))
    except Exception: db='❌'
    msgok='✅'
    try: await bot.get_chat(settings.GROUP_ID)
    except Exception: msgok='❌'
    await cb.message.answer(f'ℹ️ Diagnostic\nBot : ✅\nBase de données : {db}\nGroupe principal : {msgok}\nMessages : {msgok}\nVersion : clean-final-v5')
    await cb.answer()


@router.callback_query(F.data == 'admin:startcfg')
async def startcfg(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    await cb.message.answer('Configuration du message privé /start :', reply_markup=start_config_menu())
    await cb.answer()


@router.callback_query(F.data == 'startcfg:text')
async def startcfg_text(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    admin_state[cb.from_user.id] = {'flow':'welcome_text'}
    await cb.message.answer('Envoie le nouveau texte de bienvenue /start.')
    await cb.answer()


@router.callback_query(F.data == 'startcfg:photo')
async def startcfg_photo(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    admin_state[cb.from_user.id] = {'flow':'welcome_photo'}
    await cb.message.answer('Envoie la nouvelle photo de bienvenue /start.')
    await cb.answer()


@router.callback_query(F.data == 'startcfg:preview')
async def startcfg_preview(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    welcome = await get_setting('welcome_text','Bienvenue dans le bot Pronostic Sport. Ici tu peux consulter les pronostics en cours, donner ton avis et participer aux classements du groupe.')
    photo = await get_setting('welcome_photo','')
    if photo:
        await cb.message.answer_photo(photo, caption=welcome)
    else:
        await cb.message.answer(welcome)
    await cb.answer()


@router.callback_query(F.data == 'admin:logs')
async def logs(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    async with SessionLocal() as s:
        rows = (await s.execute(select(SecurityLog).order_by(SecurityLog.created_at.desc()).limit(10))).scalars().all()
    await cb.message.answer('\n'.join([f'{r.created_at} {r.action} {r.details or ""}' for r in rows]) or 'Aucun log')
    await cb.answer()


@router.callback_query(F.data == 'admin:roles')
async def roles(cb: CallbackQuery):
    if not is_super(cb.from_user.id): return
    await cb.message.answer('Rôles actuels chargés depuis Railway : SUPER_ADMIN_IDS, ADMIN_IDS, TRUSTED_IDS. Modification directe dans Railway pour éviter une prise de contrôle si le bot est compromis.')
    await cb.answer()
