from __future__ import annotations
import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import get_settings
from app.db.session import init_db
from app.handlers import user, admin, invites, security, moderation
from app.scheduler import setup_scheduler

async def main():
    logging.basicConfig(level=logging.INFO)
    settings=get_settings()
    await init_db()
    bot=Bot(settings.BOT_TOKEN)
    dp=Dispatcher(storage=MemoryStorage())
    dp.include_router(security.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(invites.router)
    dp.include_router(moderation.router)
    setup_scheduler(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
