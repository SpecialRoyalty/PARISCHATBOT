from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.services.matches import get_match, save_vote, render_match_message
from app.keyboards.matches import choose_winner_kb, score_kb, match_vote_url
from app.config import settings
from app.states import VoteScore

router=Router()

async def open_vote(message:Message, mid:int):
    m=await get_match(mid)
    if not m or m.status!='active':
        await message.answer('⛔ Les pronostics sont fermés.'); return
    await message.answer(f'🏟 {m.title}\n\nQui va gagner ?', reply_markup=choose_winner_kb(mid,m.team_a,m.team_b))

@router.callback_query(F.data.startswith('user:open_match:'))
async def cb_open_match(c:CallbackQuery):
    await open_vote(c.message, int(c.data.split(':')[-1])); await c.answer()

@router.callback_query(F.data.startswith('vote:'))
async def cb_vote(c:CallbackQuery, state:FSMContext):
    _,mid,winner=c.data.split(':')
    await state.update_data(vote_mid=int(mid), winner=winner)
    await state.set_state(VoteScore.score)
    await c.message.answer('Prédire le score exact ?\nExemple : 2-1', reply_markup=score_kb(int(mid)))
    await c.answer()

@router.callback_query(F.data.startswith('score:'))
async def cb_skip_score(c:CallbackQuery, state:FSMContext, bot):
    data=await state.get_data(); mid=data.get('vote_mid'); winner=data.get('winner')
    ok,reason=await save_vote(mid,c.from_user.id,winner,None)
    await state.clear()
    if ok:
        await c.message.answer('✅ Pronostic enregistré.')
        await refresh_group_match(bot, mid)
    elif reason=='duplicate': await c.message.answer('⚠️ Tu as déjà pronostiqué sur ce match.')
    else: await c.message.answer('⛔ Les pronostics sont fermés.')
    await c.answer()

@router.message(VoteScore.score, F.chat.type=='private', F.text.regexp(r'^\d+\s*-\s*\d+$'))
async def score_text(message:Message, state:FSMContext, bot):
    data=await state.get_data()
    if not data.get('vote_mid'): return
    mid=data['vote_mid']; winner=data['winner']
    score=message.text.replace(' ','')
    ok,reason=await save_vote(mid,message.from_user.id,winner,score)
    await state.clear()
    if ok:
        await message.answer('✅ Pronostic enregistré.')
        await refresh_group_match(bot, mid)
    elif reason=='duplicate': await message.answer('⚠️ Tu as déjà pronostiqué sur ce match.')
    else: await message.answer('⛔ Les pronostics sont fermés.')

async def refresh_group_match(bot, mid:int):
    m=await get_match(mid)
    if not m or m.status!='active': return
    me=await bot.get_me()
    text=await render_match_message(m)
    try:
        if m.group_message_id:
            await bot.delete_message(settings.GROUP_ID,m.group_message_id)
    except Exception: pass
    try:
        if m.photo_file_id:
            msg=await bot.send_photo(settings.GROUP_ID,m.photo_file_id,caption=text,reply_markup=match_vote_url(me.username,mid))
        else:
            msg=await bot.send_message(settings.GROUP_ID,text,reply_markup=match_vote_url(me.username,mid))
        from app.db.session import SessionLocal
        from app.db.models import Match
        async with SessionLocal() as s:
            mm=await s.get(Match,mid); mm.group_message_id=msg.message_id; await s.commit()
    except Exception as e:
        import logging; logging.exception('refresh_group_match failed: %s',e)
