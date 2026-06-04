import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import settings
from app.db.session import init_db
from app.handlers import start, user, votes, admin, trusted, super_admin, moderation
from app.services.scheduler import start_scheduler

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    bot=Bot(settings.BOT_TOKEN)
    dp=Dispatcher(storage=MemoryStorage())
    # Specific/private routers before broad group moderation
    dp.include_router(start.router)
    dp.include_router(user.router)
    dp.include_router(votes.router)
    dp.include_router(admin.router)
    dp.include_router(trusted.router)
    dp.include_router(super_admin.router)
    dp.include_router(moderation.router)
    await start_scheduler(bot)
    me=await bot.get_me()
    logging.info('Bot started: @%s', me.username)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == '__main__':
    asyncio.run(main())
