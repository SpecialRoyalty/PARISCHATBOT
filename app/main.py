import asyncio, logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.db.session import init_db, SessionLocal
from app.db.models import Match, Setting
from app.handlers import user, admin, moderation, social
from app.services.core import close_started_matches, send_leaderboard, get_setting
from app.handlers.social import share_keyboard, suggest_keyboard
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)

async def post_rules(bot:Bot):
    txt=await get_setting('rules_text','🏆 RÈGLES DU GROUPE SPORT\n\nVous pouvez discuter librement de sport, proposer des matchs et participer aux pronostics.\n\n❌ Liens interdits\n❌ Spam interdit\n❌ Insultes interdites\n❌ Ajout de bots interdit\n\nRespect et fair-play obligatoires.')
    await bot.send_message(settings.GROUP_ID, txt)

async def post_share(bot:Bot):
    await bot.send_message(settings.GROUP_ID, '📢 Partage le groupe pour faire profiter tout le monde !', reply_markup=share_keyboard())

async def post_suggest(bot:Bot):
    await bot.send_message(settings.GROUP_ID, '💡 Tu veux proposer un match ? Suggère-le à la modération.', reply_markup=suggest_keyboard())

async def periodic(bot:Bot):
    await close_started_matches(bot)

async def main():
    await init_db()
    bot=Bot(settings.BOT_TOKEN)
    dp=Dispatcher()
    # order: admin states first, user private flows, social, moderation group last
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(social.router)
    dp.include_router(moderation.router)
    sch=AsyncIOScheduler(timezone=settings.TIMEZONE)
    sch.add_job(periodic,'interval',minutes=1,args=[bot])
    sch.add_job(send_leaderboard,'interval',hours=5,args=[bot])
    sch.add_job(post_rules,'interval',hours=2,args=[bot])
    sch.add_job(post_share,'interval',hours=3,args=[bot])
    sch.add_job(post_suggest,'interval',hours=6,args=[bot])
    sch.start()
    me=await bot.get_me()
    logging.info('Bot started: @%s', me.username)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__=='__main__': asyncio.run(main())
