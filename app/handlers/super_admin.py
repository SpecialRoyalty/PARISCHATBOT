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
    except Exception: db='❌'
    await c.message.answer(f'📊 Info système\n\nBot : ✅\nPostgreSQL : {db}\nRailway : ✅\nSchedulers : ✅\nMessages : ✅\nVersion : {settings.BOT_VERSION}\n\nProchains messages : règles / partage / suggestions / classement selon planning APScheduler.')
    await c.answer()
@router.callback_query(F.data=='super:broadcast_group')
async def bg(c:CallbackQuery,state:FSMContext): await state.update_data(target='group'); await state.set_state(Broadcast.text); await c.message.answer('Message à envoyer au groupe :'); await c.answer()
@router.callback_query(F.data=='super:broadcast_private')
async def bp(c:CallbackQuery,state:FSMContext): await state.update_data(target='private'); await state.set_state(Broadcast.text); await c.message.answer('Message à envoyer à tous les PV :'); await c.answer()
@router.callback_query(F.data=='super:broadcast_category')
async def bc(c:CallbackQuery,state:FSMContext): await state.set_state(Broadcast.category); await c.message.answer('Catégorie cible ? Foot/Basket/Tennis/Boxe/MMA/Autre'); await c.answer()
@router.message(Broadcast.category)
async def bc_cat(m:Message,state:FSMContext): await state.update_data(target='category',category=m.text.strip()); await state.set_state(Broadcast.text); await m.answer('Message à envoyer :')
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
