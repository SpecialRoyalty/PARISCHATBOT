from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import settings
from app.db.session import SessionLocal
from app.db.models import Suggestion
from app.services.core import get_or_create_invite
from app.keyboards import category_keyboard

router=Router()
sugg_state={}


def share_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Je partage', callback_data='share:get')]])


def suggest_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Suggérer un match', callback_data='suggest:start')]])


def suggestion_admin_keyboard(suggestion_id:int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Accepter', callback_data=f'sugadmin:accept:{suggestion_id}'), InlineKeyboardButton(text='❌ Refuser', callback_data=f'sugadmin:refuse:{suggestion_id}')],
        [InlineKeyboardButton(text='❓ Demander précision', callback_data=f'sugadmin:more:{suggestion_id}')],
    ])


@router.callback_query(F.data=='share:get')
async def share(cb:CallbackQuery, bot:Bot):
    link=await get_or_create_invite(bot, cb.from_user.id)
    await cb.message.answer(f'📢 Voici ton lien unique :\n{link}')
    await cb.answer()


@router.callback_query(F.data=='suggest:start')
async def sug_start(cb:CallbackQuery):
    sugg_state[cb.from_user.id]={'step':'category'}
    await cb.message.answer('Choisis la catégorie du match à suggérer :', reply_markup=category_keyboard('sugcat'))
    await cb.answer()


@router.callback_query(F.data.startswith('sugcat:'))
async def sug_category(cb:CallbackQuery):
    sugg_state[cb.from_user.id]={'step':'title', 'category': cb.data.split(':',1)[1]}
    await cb.message.answer(f'✅ Catégorie : {cb.data.split(":",1)[1]}\nTitre du match ?\nExemple : France 🇫🇷 vs Côte d’Ivoire 🇨🇮')
    await cb.answer()


@router.message(lambda m: m.chat.type == 'private' and m.from_user and m.from_user.id in sugg_state)
async def sug_text(message:Message, bot:Bot):
    st=sugg_state.get(message.from_user.id)
    if not st: return
    if st['step']=='category':
        await message.answer('Utilise les boutons pour choisir la catégorie.', reply_markup=category_keyboard('sugcat'))
        return
    if st['step']=='title':
        st['title']=(message.text or '').strip(); st['step']='date'
        await message.answer('Date/heure si connue ?\nTu peux aussi écrire : Je ne sais pas')
        return
    if st['step']=='date':
        st['date']=(message.text or '').strip(); st['step']='photo'
        await message.answer('Image optionnelle : envoie une photo ou écris SKIP.')
        return
    if st['step']=='photo':
        photo=message.photo[-1].file_id if message.photo else None
        async with SessionLocal() as s:
            obj=Suggestion(user_id=message.from_user.id,category=st['category'],title=st['title'],proposed_date=st['date'],photo_file_id=photo)
            s.add(obj); await s.commit(); await s.refresh(obj)
        for aid in settings.admin_ids:
            try:
                txt=f'💡 Nouvelle suggestion #{obj.id}\nCatégorie: {obj.category}\nMatch: {obj.title}\nDate: {obj.proposed_date}\nUtilisateur: {message.from_user.id}'
                if photo:
                    await bot.send_photo(aid, photo, caption=txt, reply_markup=suggestion_admin_keyboard(obj.id))
                else:
                    await bot.send_message(aid, txt, reply_markup=suggestion_admin_keyboard(obj.id))
            except Exception: pass
        sugg_state.pop(message.from_user.id,None)
        await message.answer('✅ Suggestion envoyée à la modération.')


@router.callback_query(F.data.startswith('sugadmin:'))
async def sug_admin(cb:CallbackQuery):
    if cb.from_user.id not in settings.admin_ids:
        return
    _, action, sid = cb.data.split(':')
    sid=int(sid)
    async with SessionLocal() as s:
        obj=await s.get(Suggestion, sid)
        if not obj:
            await cb.message.answer('Suggestion introuvable.'); await cb.answer(); return
        if action=='accept': obj.status='accepted'; msg='✅ Suggestion acceptée.'
        elif action=='refuse': obj.status='refused'; msg='❌ Suggestion refusée.'
        else: obj.status='needs_more_info'; msg='❓ Précision demandée. Contacte l’utilisateur manuellement avec son ID.'
        await s.commit()
    await cb.message.answer(msg)
    await cb.answer()
