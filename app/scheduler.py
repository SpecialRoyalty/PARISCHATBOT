from __future__ import annotations
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, func, desc
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Match, Prediction, ScheduledMessage, Invitation, User
from app.services.matches import publish_match, publish_trend, trend_interval_minutes, close_due_matches, ranking_text
from app.services.common import replace_group_message, get_setting, anonymize, now_utc
settings=get_settings()

scheduler=AsyncIOScheduler(timezone=settings.TIMEZONE)

async def tick_matches(bot:Bot):
    async with SessionLocal() as session:
        await close_due_matches(bot,session)
        matches=(await session.execute(select(Match).where(Match.status=='active', Match.starts_at>now_utc()))).scalars().all()
        for m in matches:
            # prono toutes les 30 min
            sm=await session.get(ScheduledMessage,f'match:{m.id}:prono')
            if not sm or not sm.sent_at or now_utc()-sm.sent_at >= timedelta(minutes=settings.PRONO_REPOST_MINUTES):
                await publish_match(bot,session,m)
            total=(await session.execute(select(func.count(Prediction.id)).where(Prediction.match_id==m.id))).scalar_one()
            interval=trend_interval_minutes(total)
            smt=await session.get(ScheduledMessage,f'match:{m.id}:trend')
            if not smt or not smt.sent_at or now_utc()-smt.sent_at >= timedelta(minutes=interval):
                await publish_trend(bot,session,m)

async def publish_leaderboard(bot:Bot):
    async with SessionLocal() as session:
        text=await ranking_text(session,10)
        await replace_group_message(bot,session,'leaderboard',text)

async def publish_rules(bot:Bot):
    async with SessionLocal() as session:
        rules=await get_setting(session,'rules_text','📌 Règles du groupe\n\nRespect obligatoire.\nPas d’insultes.\nPas de liens.\nPas de spam.\nPas de commandes bot.')
        await replace_group_message(bot,session,'rules',rules)

async def publish_share(bot:Bot):
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Je partage', callback_data='invite:get')]])
    async with SessionLocal() as session:
        await replace_group_message(bot,session,'share','📢 Partage le groupe pour faire profiter tout le monde !\n\nInvite tes amis passionnés de sport et monte dans le classement des meilleurs inviteurs.',kb)

async def publish_suggestion(bot:Bot):
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Suggérer un match', callback_data='suggest:start')]])
    async with SessionLocal() as session:
        await replace_group_message(bot,session,'suggestion','💡 Tu veux proposer un match ?\n\nSuggère un match à la modération.',kb)

async def publish_top_inviters(bot:Bot):
    async with SessionLocal() as session:
        rows=(await session.execute(select(Invitation.inviter_id, func.count(Invitation.id)).group_by(Invitation.inviter_id).order_by(desc(func.count(Invitation.id))).limit(10))).all()
        lines=['🏅 TOP INVITEURS DU JOUR\n']
        medals=['🥇','🥈','🥉']
        for i,(uid,count) in enumerate(rows):
            u=await session.get(User,uid)
            lines.append(f"{medals[i] if i<3 else '🏅'} {anonymize((u.first_name or u.username) if u else str(uid))} : {count} invitations")
        await replace_group_message(bot,session,'top_inviters','\n'.join(lines) if rows else '🏅 TOP INVITEURS DU JOUR\n\nAucune invitation comptabilisée.')

async def cleanup_timed_messages(bot:Bot):
    # Supprime classement et top inviteurs après 1h
    async with SessionLocal() as session:
        for key in ['leaderboard','top_inviters']:
            sm=await session.get(ScheduledMessage,key)
            if sm and sm.message_id and sm.sent_at and now_utc()-sm.sent_at>=timedelta(hours=1):
                try: await bot.delete_message(settings.GROUP_ID,sm.message_id)
                except Exception: pass
                sm.message_id=None; await session.commit()

def setup_scheduler(bot:Bot):
    scheduler.add_job(tick_matches,'interval',minutes=1,args=[bot],id='tick_matches',replace_existing=True)
    scheduler.add_job(publish_leaderboard,'interval',hours=settings.LEADERBOARD_HOURS,args=[bot],id='leaderboard',replace_existing=True)
    scheduler.add_job(publish_rules,'interval',hours=settings.RULES_HOURS,args=[bot],id='rules',replace_existing=True)
    scheduler.add_job(publish_share,'interval',hours=settings.SHARE_HOURS,args=[bot],id='share',replace_existing=True)
    scheduler.add_job(publish_suggestion,'interval',hours=settings.SUGGESTION_HOURS,args=[bot],id='suggestion',replace_existing=True)
    scheduler.add_job(publish_top_inviters,'cron',hour=12,minute=0,args=[bot],id='top_inviters',replace_existing=True)
    scheduler.add_job(cleanup_timed_messages,'interval',minutes=5,args=[bot],id='cleanup',replace_existing=True)
    scheduler.start()
