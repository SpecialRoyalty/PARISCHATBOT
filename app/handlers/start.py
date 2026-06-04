from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from app.keyboards.common import user_panel, role_choice, trusted_panel, admin_panel, super_panel
from app.services.roles import roles_for
from app.services.settings import get_setting, DEFAULT_START
from app.services.users import upsert_user
from app.services.matches import active_matches
from app.keyboards.matches import active_matches_kb

router=Router()

async def show_user_panel_msg(msg:Message):
    start_text=await get_setting('start_text', DEFAULT_START)
    photo=await get_setting('start_photo', None)
    if photo:
        await msg.answer_photo(photo, caption=start_text, reply_markup=user_panel())
    else:
        await msg.answer(start_text, reply_markup=user_panel())

@router.message(CommandStart())
async def start(message:Message):
    await upsert_user(message.from_user)
    arg=(message.text or '').split(maxsplit=1)
    if len(arg)>1 and arg[1].startswith('vote_'):
        mid=int(arg[1].split('_',1)[1])
        from app.handlers.votes import open_vote
        await open_vote(message, mid); return
    r=await roles_for(message.from_user.id)
    if r:
        await message.answer('Bienvenue 👋\nChoisis ton espace :', reply_markup=role_choice('super_admin' in r, 'admin' in r, 'trusted' in r))
    else:
        await show_user_panel_msg(message)

@router.callback_query(F.data=='nav:user')
async def cb_user(c:CallbackQuery):
    await c.message.edit_text('👤 Panel utilisateur', reply_markup=user_panel()); await c.answer()
@router.callback_query(F.data=='nav:trusted')
async def cb_trusted(c:CallbackQuery):
    await c.message.edit_text('🤝 Panel Trusted', reply_markup=trusted_panel()); await c.answer()
@router.callback_query(F.data=='nav:admin')
async def cb_admin(c:CallbackQuery):
    await c.message.edit_text('🛡 Panel Admin', reply_markup=admin_panel()); await c.answer()
@router.callback_query(F.data=='nav:super')
async def cb_super(c:CallbackQuery):
    await c.message.edit_text('👑 Panel Super Admin', reply_markup=super_panel()); await c.answer()

@router.callback_query(F.data=='user:matches')
async def user_matches(c:CallbackQuery):
    ms=await active_matches()
    if not ms:
        await c.message.edit_text('Aucun pronostic actif pour le moment.', reply_markup=user_panel())
    else:
        await c.message.edit_text('🏟 Pronostics en cours :', reply_markup=active_matches_kb(ms))
    await c.answer()
