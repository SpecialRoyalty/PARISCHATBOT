from datetime import datetime, timedelta
from sqlalchemy import select, func
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from app.config import settings
from app.db.session import SessionLocal
from app.db.models import User, Match, Prediction, Setting, SecurityLog, InviteLink
from app.utils.text import anonymize
from app.keyboards import match_vote_group

async def log(action: str, details: str = '', actor_id: int | None = None):
    async with SessionLocal() as s:
        s.add(SecurityLog(action=action, details=details, actor_id=actor_id))
        await s.commit()

async def upsert_user(tg_user):
    async with SessionLocal() as s:
        u = await s.get(User, tg_user.id)
        full_old = None if not u else f"{u.first_name or ''} {u.last_name or ''}".strip()
        full_new = f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip()
        if not u:
            u=User(id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name, last_name=tg_user.last_name)
            s.add(u)
        else:
            if (u.username or '') != (tg_user.username or '') or (full_old or '') != (full_new or ''):
                from app.db.models import IdentityHistory
                s.add(IdentityHistory(user_id=u.id, old_name=full_old, new_name=full_new, old_username=u.username, new_username=tg_user.username))
                u.username=tg_user.username; u.first_name=tg_user.first_name; u.last_name=tg_user.last_name
        await s.commit()
        return u

async def get_setting(key: str, default: str = '') -> str:
    async with SessionLocal() as s:
        obj=await s.get(Setting,key)
        return obj.value if obj and obj.value is not None else default

async def set_setting(key: str, value: str):
    async with SessionLocal() as s:
        obj=await s.get(Setting,key)
        if obj: obj.value=value
        else: s.add(Setting(key=key,value=value))
        await s.commit()

async def active_matches():
    async with SessionLocal() as s:
        res=await s.execute(select(Match).where(Match.status=='active').order_by(Match.start_at))
        return list(res.scalars())

async def publish_match(bot: Bot, match: Match):
    text=f"🏟 {match.title}\n\n📅 Début : {match.start_at.strftime('%d/%m/%Y à %H:%M')}\n🏆 Catégorie : {match.category}\n\n👇 Donne ton pronostic"
    try:
        if match.group_message_id:
            await bot.delete_message(settings.GROUP_ID, match.group_message_id)
    except Exception:
        pass
    msg = await bot.send_photo(settings.GROUP_ID, match.photo_file_id, caption=text, reply_markup=match_vote_group(settings.BOT_USERNAME, match.id)) if match.photo_file_id else await bot.send_message(settings.GROUP_ID, text, reply_markup=match_vote_group(settings.BOT_USERNAME, match.id))
    async with SessionLocal() as s:
        m=await s.get(Match, match.id); m.group_message_id=msg.message_id; await s.commit()

async def trend_text(match_id:int):
    async with SessionLocal() as s:
        m=await s.get(Match, match_id)
        rows=(await s.execute(select(Prediction).where(Prediction.match_id==match_id))).scalars().all()
        total=len(rows)
        ca=sum(1 for r in rows if r.winner=='a'); cb=sum(1 for r in rows if r.winner=='b'); cd=sum(1 for r in rows if r.winner=='draw')
        pct=lambda n: int(round((n/total)*100)) if total else 0
        # top 10 by success with >=10 participations
        top=(await s.execute(select(User).where(User.total>=10).order_by((User.correct*1.0/User.total).desc(), User.total.desc()).limit(10))).scalars().all()
        top_ids={u.id for u in top}
        top_voted=sum(1 for r in rows if r.user_id in top_ids)
        return (f"📊 {m.title}\n\n👥 {total} participants\n\n{m.option_a} : {pct(ca)}%\n{m.option_b} : {pct(cb)}%\n🤝 Match nul : {pct(cd)}%\n\n🔥 {top_voted} membres du Top 10 ont déjà pronostiqué\n\n⚡ Faites votre pronostic avant le début du match !")

async def update_trend(bot: Bot, match_id:int):
    async with SessionLocal() as s:
        m=await s.get(Match, match_id)
        if not m or m.status!='active': return
        text=await trend_text(match_id)
        if m.trend_message_id:
            try: await bot.delete_message(settings.GROUP_ID, m.trend_message_id)
            except Exception: pass
        msg = await bot.send_photo(settings.GROUP_ID, m.photo_file_id, caption=text) if m.photo_file_id else await bot.send_message(settings.GROUP_ID, text)
        m.trend_message_id=msg.message_id
        await s.commit()

async def close_started_matches(bot: Bot):
    now=datetime.utcnow()
    async with SessionLocal() as s:
        matches=(await s.execute(select(Match).where(Match.status=='active', Match.vote_close_at<=now))).scalars().all()
        for m in matches:
            m.status='locked'
            for mid in [m.group_message_id,m.trend_message_id]:
                if mid:
                    try: await bot.delete_message(settings.GROUP_ID, mid)
                    except Exception: pass
            m.group_message_id=None; m.trend_message_id=None
            for aid in settings.admin_ids:
                try: await bot.send_message(aid, f"⏱ Match fermé aux votes : {m.title}\nClôture le résultat dans le panel admin.")
                except Exception: pass
        await s.commit()

async def send_leaderboard(bot: Bot):
    async with SessionLocal() as s:
        users=(await s.execute(select(User).where(User.total>=10).order_by((User.correct*1.0/User.total).desc(), User.total.desc(), User.exact_scores.desc()).limit(10))).scalars().all()
        if not users: return
        lines=['🏆 TOP PRONOSTIQUEURS\n']
        medals=['🥇','🥈','🥉']
        for i,u in enumerate(users):
            rate=round(u.correct/u.total*100) if u.total else 0
            badge='👑 Légende' if rate>=80 and u.total>=250 else '🏆 Expert Sport' if rate>=75 and u.total>=100 else '📈 Régulier' if u.total>=100 else '💬 Actif'
            lines.append(f"{medals[i] if i<3 else '🏅'} {anonymize(u.first_name,u.id)}\n📊 {rate}%\n📝 {u.total} participations\n🎯 {u.exact_scores} scores exacts\n{badge}\n")
        msg=await bot.send_message(settings.GROUP_ID, '\n'.join(lines))
        # schedule deletion handled by scheduler job below with one-off APScheduler in main
        return msg.message_id

async def get_or_create_invite(bot: Bot, user_id:int):
    async with SessionLocal() as s:
        obj=await s.get(InviteLink,user_id)
        if obj: return obj.link
        invite=await bot.create_chat_invite_link(settings.GROUP_ID, name=f'invite_{user_id}', creates_join_request=False)
        s.add(InviteLink(user_id=user_id, link=invite.invite_link)); await s.commit(); return invite.invite_link
