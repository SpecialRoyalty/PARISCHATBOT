from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.config import settings
from app.services.settings import get_setting, DEFAULT_RULES
from app.services.matches import lock_started_matches, matches_to_close, active_matches
from app.db.session import SessionLocal
from app.db.models import User, Role, Match
from app.utils.text import anonymize
from app.keyboards.common import kb
from app.keyboards.matches import close_result_kb

scheduler=AsyncIOScheduler(timezone=settings.TIMEZONE)

async def post_rules(bot):
    text=await get_setting('rules_text', DEFAULT_RULES)
    try: await bot.send_message(settings.GROUP_ID,text)
    except Exception: pass
async def post_share(bot):
    try: await bot.send_message(settings.GROUP_ID,'📢 Fais découvrir le groupe à tes amis !', reply_markup=kb([[('Je partage','user:share')]]))
    except Exception: pass
async def post_suggest(bot):
    try: await bot.send_message(settings.GROUP_ID,'💡 Tu veux proposer un match ?', reply_markup=kb([[('Suggérer un match','user:suggest')]]))
    except Exception: pass
async def send_leaderboard(bot):
    async with SessionLocal() as s:
        users=(await s.execute(select(User).where(User.total_predictions>=10).order_by((User.good_predictions*1.0/User.total_predictions).desc(), User.total_predictions.desc()).limit(10))).scalars().all()
    if not users: return
    lines=['🏆 TOP PRONOSTIQUEURS\n']
    for i,u in enumerate(users,1):
        pct=round(u.good_predictions*100/u.total_predictions) if u.total_predictions else 0
        lines.append(f'{i}. {anonymize(u.first_name or u.username)} — {pct}% | {u.total_predictions} participations | 🎯 {u.exact_scores}')
    try:
        await bot.send_message(settings.GROUP_ID,'\n'.join(lines))
    except Exception: pass
async def periodic(bot):
    await lock_started_matches(bot)
    due=await matches_to_close()
    if not due: return
    async with SessionLocal() as s:
        ids=(await s.execute(select(Role.user_id).where(Role.role.in_(['admin','super_admin'])))).scalars().all()
    for m in due:
        for uid in set(ids):
            try: await bot.send_message(uid,f'⏱ Match terminé : {m.title}\nQui a gagné ?',reply_markup=close_result_kb(m.id,m.team_a,m.team_b))
            except Exception: pass
async def start_scheduler(bot):
    scheduler.add_job(post_rules,'interval',hours=settings.RULES_HOURS,args=[bot],id='rules',replace_existing=True)
    scheduler.add_job(post_share,'interval',hours=settings.SHARE_HOURS,args=[bot],id='share',replace_existing=True)
    scheduler.add_job(post_suggest,'interval',hours=settings.SUGGESTION_HOURS,args=[bot],id='suggest',replace_existing=True)
    scheduler.add_job(send_leaderboard,'interval',hours=settings.LEADERBOARD_HOURS,args=[bot],id='leaderboard',replace_existing=True)
    scheduler.add_job(periodic,'interval',minutes=1,args=[bot],id='periodic',replace_existing=True)
    scheduler.start()
