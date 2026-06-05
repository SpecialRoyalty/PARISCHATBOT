from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from app.services.roles import is_super, add_role, remove_role
from app.services.settings import set_setting, get_setting, DEFAULT_START
from app.services.moderation import list_hashes, delete_hash, add_media_hash, hash_message_media
from app.services.users import all_users
from app.states import SetStartText, SetStartPhoto, Broadcast, RoleEdit, AddHash
from app.keyboards.common import super_panel, kb
from app.config import settings
from app.db.session import SessionLocal, engine
from app.db.models import SecurityLog, User
from app.services.badges import badge_health
router=Router()
async def guard(c):
    if not await is_super(c.from_user.id): await c.answer('Accès refusé', show_alert=True); return False
    return True
@router.callback_query(F.data=='super:start_text')
async def start_text(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.set_state(SetStartText.text); await c.message.answer('Envoie le nouveau texte /start :'); await c.answer()
@router.message(SetStartText.text)
async def save_start_text(m:Message,state:FSMContext): await set_setting('start_text',m.text); await state.clear(); await m.answer('✅ Texte /start sauvegardé.')
@router.callback_query(F.data=='super:start_photo')
async def start_photo(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.set_state(SetStartPhoto.photo); await c.message.answer('Envoie la nouvelle photo /start :'); await c.answer()
@router.message(SetStartPhoto.photo, F.photo)
async def save_start_photo(m:Message,state:FSMContext): await set_setting('start_photo',m.photo[-1].file_id); await state.clear(); await m.answer('✅ Photo /start sauvegardée.')
@router.callback_query(F.data=='super:info')
async def info(c:CallbackQuery):
    if not await guard(c): return
    db='❌'
    try:
        async with engine.begin() as conn: await conn.exec_driver_sql('SELECT 1')
        db='✅'
    except Exception:
        db='❌'
    try:
        from app.services.scheduler import scheduler
        jobs={j.id:j.next_run_time for j in scheduler.get_jobs()}
        sched='✅' if all(jobs.get(x) is not None for x in ['periodic','leaderboard','rules','share','suggest']) else '⚠️'
        schedule_lines='\n'.join(f'• {k} : {jobs.get(k)}' for k in ['periodic','leaderboard','rules','share','suggest'])
    except Exception as e:
        sched='❌'; schedule_lines=f'Impossible de lire les tâches : {e}'
    try:
        bh=await badge_health()
        badge_text=(f"{bh['status']} — {bh['badges']} badges attribués\n"
                    f"Éligibles participation: {bh['eligible_active']} | scores exacts: {bh['eligible_exact']} | invitations: {bh['eligible_invite']}")
    except Exception as e:
        badge_text=f'❌ Erreur vérification badges : {e}'
    await c.message.answer(
        f'📊 Info système\n\n'
        f'Bot : ✅\nPostgreSQL : {db}\nRailway : ✅\nSchedulers : {sched}\nMessages : ✅\nVersion : {settings.BOT_VERSION}\n\n'
        f'⏱ Prochaines publications\n{schedule_lines}\n\n'
        f'🎖 Vérification badges\n{badge_text}'
    )
    await c.answer()
@router.callback_query(F.data=='super:broadcast_group')
async def bg(c:CallbackQuery,state:FSMContext): await state.update_data(target='group'); await state.set_state(Broadcast.text); await c.message.answer('Message à envoyer au groupe :'); await c.answer()
@router.callback_query(F.data=='super:broadcast_private')
async def bp(c:CallbackQuery,state:FSMContext): await state.update_data(target='private'); await state.set_state(Broadcast.text); await c.message.answer('Message à envoyer à tous les PV :'); await c.answer()
@router.callback_query(F.data=='super:broadcast_category')
async def bc(c:CallbackQuery,state:FSMContext):
    from app.keyboards.common import category_kb
    await state.set_state(Broadcast.category)
    await c.message.answer('Catégorie cible ?', reply_markup=category_kb('bcat'))
    await c.answer()
@router.callback_query(F.data.startswith('bcat:'))
async def bc_cat_cb(c:CallbackQuery,state:FSMContext):
    await state.update_data(target='category', category=c.data.split(':',1)[1])
    await state.set_state(Broadcast.text)
    await c.message.answer('Message à envoyer :')
    await c.answer()
@router.message(Broadcast.text)
async def b_send(m:Message,state:FSMContext,bot):
    d=await state.get_data(); sent=0
    if d['target']=='group': await bot.send_message(settings.GROUP_ID,m.text); sent=1
    else:
        users=await all_users()
        for u in users:
            if d['target']=='category' and u.category_pref!=d.get('category'): continue
            try: await bot.send_message(u.id,m.text); sent+=1
            except Exception: pass
    await state.clear(); await m.answer(f'✅ Broadcast envoyé ({sent}).')
@router.callback_query(F.data=='super:admins')
async def admins_menu(c:CallbackQuery):
    await c.message.edit_text('Gestion Admins', reply_markup=kb([[('➕ Ajouter Admin','super:add_admin'),('➖ Retirer Admin','super:del_admin')],[('⬅ Retour','nav:super')]])); await c.answer()
@router.callback_query(F.data=='super:trusted')
async def trusted_menu(c:CallbackQuery):
    await c.message.edit_text('Gestion Trusted', reply_markup=kb([[('➕ Ajouter Trusted','super:add_trusted'),('➖ Retirer Trusted','super:del_trusted')],[('⬅ Retour','nav:super')]])); await c.answer()
@router.callback_query(F.data.startswith('super:add_')|F.data.startswith('super:del_'))
async def role_prompt(c:CallbackQuery,state:FSMContext):
    mapping={'super:add_admin':RoleEdit.add_admin,'super:del_admin':RoleEdit.del_admin,'super:add_trusted':RoleEdit.add_trusted,'super:del_trusted':RoleEdit.del_trusted}
    await state.set_state(mapping[c.data]); await c.message.answer('Envoie le Telegram ID :'); await c.answer()
@router.message(RoleEdit.add_admin)
async def addadm(m:Message,state:FSMContext): await add_role(int(m.text),'admin'); await state.clear(); await m.answer('✅ Admin ajouté.')
@router.message(RoleEdit.del_admin)
async def deladm(m:Message,state:FSMContext): await remove_role(int(m.text),'admin'); await state.clear(); await m.answer('✅ Admin retiré.')
@router.message(RoleEdit.add_trusted)
async def addtr(m:Message,state:FSMContext): await add_role(int(m.text),'trusted'); await state.clear(); await m.answer('✅ Trusted ajouté.')
@router.message(RoleEdit.del_trusted)
async def deltr(m:Message,state:FSMContext): await remove_role(int(m.text),'trusted'); await state.clear(); await m.answer('✅ Trusted retiré.')
@router.callback_query(F.data=='super:hashes')
async def hashes(c:CallbackQuery): await c.message.edit_text('Médias interdits', reply_markup=kb([[('➕ Ajouter hash média','super:add_hash')],[('📋 Voir hash','super:hash_list')],[('❌ Supprimer hash','super:hash_del')],[('⬅ Retour','nav:super')]])); await c.answer()
@router.callback_query(F.data=='super:add_hash')
async def add_hash(c:CallbackQuery,state:FSMContext): await state.set_state(AddHash.media); await c.message.answer('Envoie le média à interdire :'); await c.answer()
@router.message(AddHash.media)
async def add_hash_msg(m:Message,state:FSMContext,bot):
    h,t=await hash_message_media(bot,m)
    if h: await add_media_hash(h,t,m.from_user.id); await m.answer('✅ Média interdit ajouté.')
    else: await m.answer('Aucun média détecté.')
    await state.clear()
@router.callback_query(F.data=='super:hash_list')
async def hlist(c:CallbackQuery):
    hs=await list_hashes(); await c.message.answer('\n'.join(f'#{h.id} {h.media_type} {h.hash[:16]}...' for h in hs) or 'Aucun hash.'); await c.answer()
@router.callback_query(F.data=='super:logs')
async def logs(c:CallbackQuery):
    async with SessionLocal() as s:
        logs=(await s.execute(select(SecurityLog).order_by(SecurityLog.id.desc()).limit(20))).scalars().all()
    await c.message.answer('\n'.join(f'#{l.id} {l.event} {l.user_id} {l.details or ""}' for l in logs) or 'Aucun log.'); await c.answer()

@router.callback_query(F.data=='super:freq')
async def freq(c:CallbackQuery):
    if not await guard(c): return
    try:
        from app.services.scheduler import scheduler
        jobs={j.id:j for j in scheduler.get_jobs()}
        lines=['⏱ Fréquences / prochaines publications\n']
        labels={'periodic':'verrouillage matchs + clôtures','leaderboard':'classement','rules':'règles','share':'partage','suggest':'suggestion'}
        for jid in ['periodic','leaderboard','rules','share','suggest']:
            j=jobs.get(jid)
            if j:
                lines.append(f"• {jid} ({labels[jid]}) : prochain passage {j.next_run_time}")
            else:
                lines.append(f"• {jid} ({labels[jid]}) : ❌ non planifié")
    except Exception as e:
        lines=['⏱ Fréquences','Impossible de lire le scheduler.',str(e)]
    await c.message.answer('\n'.join(lines), reply_markup=super_panel())
    await c.answer()

@router.callback_query(F.data=='super:hash_del')
async def hash_del_prompt(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await c.message.answer('Envoie : supprimer hash <id>')
    await c.answer()

@router.message(F.text.startswith('supprimer hash '))
async def hash_del_msg(m:Message):
    if not await is_super(m.from_user.id): return
    try:
        hid=int(m.text.split()[-1])
        await delete_hash(hid)
        await m.answer('✅ Hash supprimé si existant.')
    except Exception:
        await m.answer('Format invalide. Exemple : supprimer hash 12')
