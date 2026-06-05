from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import select
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import settings
from app.services.settings import get_setting, set_setting, DEFAULT_RULES
from app.services.matches import lock_started_matches, matches_to_close
from app.db.session import SessionLocal
from app.db.models import User, Role
from app.utils.text import anonymize
from app.keyboards.matches import close_result_kb

scheduler=AsyncIOScheduler(timezone=settings.TIMEZONE)

async def _delete_old(bot, key:str):
    old=await get_setting(key, None)
    if old:
        try:
            await bot.delete_message(settings.GROUP_ID, int(old))
        except Exception:
            pass

async def _send_unique(bot, key:str, text:str, reply_markup=None):
    await _delete_old(bot, key)
    msg=await bot.send_message(settings.GROUP_ID, text, reply_markup=reply_markup)
    await set_setting(key, str(msg.message_id))
    return msg

async def _bot_username(bot):
    me=await bot.get_me()
    return me.username

async def post_rules(bot):
    text=await get_setting('rules_text', DEFAULT_RULES)
    try:
        await _send_unique(bot,'rules_message_id',text)
    except Exception:
        pass

async def post_share(bot):
    try:
        username=await _bot_username(bot)
        markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Je partage', url=f'https://t.me/{username}?start=share')]])
        await _send_unique(bot,'share_message_id','📢 Fais découvrir le groupe à tes amis !', reply_markup=markup)
    except Exception:
        pass

async def post_suggest(bot):
    try:
        username=await _bot_username(bot)
        markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Suggérer un match', url=f'https://t.me/{username}?start=suggest')]])
        await _send_unique(bot,'suggest_message_id','💡 Tu veux proposer un match ?', reply_markup=markup)
    except Exception:
        pass

async def send_leaderboard(bot):
    async with SessionLocal() as s:
        users=(await s.execute(select(User).where(User.total_predictions>=10).order_by((User.good_predictions*1.0/User.total_predictions).desc(), User.total_predictions.desc()).limit(10))).scalars().all()
    if not users: return
    lines=['🏆 TOP PRONOSTIQUEURS\n']
    for i,u in enumerate(users,1):
        pct=round(u.good_predictions*100/u.total_predictions) if u.total_predictions else 0
        lines.append(f'{i}. {anonymize(u.first_name or u.username)} — {pct}% | {u.total_predictions} participations | 🎯 {u.exact_scores}')
    try:
        await _send_unique(bot,'leaderboard_message_id','\n'.join(lines))
    except Exception:
        pass

async def periodic(bot):
    await lock_started_matches(bot)
    due=await matches_to_close()
    if not due: return
    async with SessionLocal() as s:
        ids=(await s.execute(select(Role.user_id).where(Role.role.in_(['admin','super_admin'])))).scalars().all()
    for m in due:
        for uid in set(ids):
            try:
                await bot.send_message(uid,f'⏱ Match terminé : {m.title}\nQui a gagné ?',reply_markup=close_result_kb(m.id,m.team_a,m.team_b))
            except Exception:
                pass

async def start_scheduler(bot):
    now=datetime.now(settings.tz)
    # Important: do NOT use next_run_time=None here. In APScheduler that pauses the job,
    # which is why the Info panel showed rules/share/suggest = None.
    scheduler.add_job(post_rules,'interval',hours=settings.RULES_HOURS,args=[bot],id='rules',replace_existing=True, next_run_time=now+timedelta(seconds=20))
    scheduler.add_job(post_share,'interval',hours=settings.SHARE_HOURS,args=[bot],id='share',replace_existing=True, next_run_time=now+timedelta(seconds=40))
    scheduler.add_job(post_suggest,'interval',hours=settings.SUGGESTION_HOURS,args=[bot],id='suggest',replace_existing=True, next_run_time=now+timedelta(seconds=60))
    scheduler.add_job(send_leaderboard,'interval',hours=settings.LEADERBOARD_HOURS,args=[bot],id='leaderboard',replace_existing=True, next_run_time=now+timedelta(seconds=80))
    scheduler.add_job(periodic,'interval',minutes=1,args=[bot],id='periodic',replace_existing=True, next_run_time=now+timedelta(seconds=10))
    if not scheduler.running:
        scheduler.start()
