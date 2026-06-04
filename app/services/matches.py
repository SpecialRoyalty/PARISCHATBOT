from __future__ import annotations
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from aiogram import Bot
from app.db.models import Match, Prediction, UserStats, Badge, User
from app.keyboards import match_vote_kb, close_match_kb
from app.services.common import local_dt_str, anonymize, replace_group_message, now_utc
from app.config import get_settings
settings=get_settings()


def split_sides(title:str):
    for sep in [' vs ', ' VS ', ' Vs ', ' v ', ' - ', ' contre ']:
        if sep in title:
            a,b=title.split(sep,1); return a.strip(), b.strip()
    return 'Équipe A','Équipe B'

def match_text(m:Match):
    return f"🏟 {m.title}\n\n📅 Début : {local_dt_str(m.starts_at)}\n🏆 Catégorie : {m.category}\n\n👇 Donne ton pronostic"

def trend_interval_minutes(participants:int)->int:
    if participants < 50: return 120
    if participants <= 200: return 60
    return 30

async def publish_match(bot:Bot, session, m:Match):
    msg=await replace_group_message(bot,session,f'match:{m.id}:prono',match_text(m),match_vote_kb(m.id),m.image_file_id)
    m.last_prono_message_id=msg.message_id; await session.commit()

async def publish_trend(bot:Bot, session, m:Match):
    rows=(await session.execute(select(Prediction.choice, func.count(Prediction.id)).where(Prediction.match_id==m.id).group_by(Prediction.choice))).all()
    counts={k:v for k,v in rows}; total=sum(counts.values())
    def pct(k): return round((counts.get(k,0)*100/total),1) if total else 0
    top_ids=[r[0] for r in (await session.execute(select(UserStats.user_id).where(UserStats.participations>=settings.MIN_RANKING_PARTICIPATIONS).order_by(desc(UserStats.correct*1.0/UserStats.participations),desc(UserStats.participations)).limit(10))).all()]
    top_part=0
    if top_ids:
        top_part=(await session.execute(select(func.count(Prediction.id)).where(Prediction.match_id==m.id, Prediction.user_id.in_(top_ids)))).scalar_one()
    text=f"📊 {m.title}\n\n👥 {total} participants\n\n{m.side_a} : {pct('A')}%\n{m.side_b} : {pct('B')}%\n🤝 Match nul : {pct('DRAW')}%\n\n🔥 {top_part} membres du Top 10 ont déjà pronostiqué\n\n⚡ Faites votre pronostic avant le début du match !"
    msg=await replace_group_message(bot,session,f'match:{m.id}:trend',text,None,m.image_file_id)
    m.last_trend_message_id=msg.message_id; await session.commit()

async def active_matches(session):
    return (await session.execute(select(Match).where(Match.status=='active', Match.starts_at>now_utc()).order_by(Match.starts_at))).scalars().all()

async def close_due_matches(bot:Bot, session):
    now=now_utc()
    matches=(await session.execute(select(Match).where(Match.status=='active', Match.starts_at<=now))).scalars().all()
    for m in matches:
        m.status='pending_result'
        for key in [f'match:{m.id}:prono', f'match:{m.id}:trend']:
            from app.db.models import ScheduledMessage
            sm=await session.get(ScheduledMessage,key)
            if sm and sm.message_id:
                try: await bot.delete_message(settings.GROUP_ID, sm.message_id)
                except Exception: pass
        await session.commit()
        for aid in settings.admin_ids:
            try: await bot.send_message(aid, f"Le match {m.title} est commencé/terminé à clôturer.", reply_markup=close_match_kb(m.id,m.side_a,m.side_b))
            except Exception: pass

async def apply_result(session, match_id:int, winner:str, final_score:str|None):
    m=await session.get(Match,match_id); 
    if not m: return None
    m.winner=winner; m.final_score=final_score; m.status='cancelled' if winner=='CANCEL' else 'closed'
    preds=(await session.execute(select(Prediction).where(Prediction.match_id==match_id))).scalars().all()
    if winner!='CANCEL':
        for p in preds:
            p.is_correct=(p.choice==winner)
            p.score_exact_correct=bool(final_score and p.exact_score and p.exact_score.replace(':','-').replace(' ','')==final_score.replace(':','-').replace(' ',''))
            st=await session.get(UserStats,p.user_id) or UserStats(user_id=p.user_id)
            if st.user_id is None: pass
            session.add(st)
            st.participations += 1
            if p.is_correct: st.correct += 1
            if p.score_exact_correct: st.exact_scores += 1
            u=await session.get(User,p.user_id)
            if u:
                if p.is_correct: u.good_streak+=1; u.best_streak=max(u.best_streak,u.good_streak)
                else: u.good_streak=0
            await update_badges(session,p.user_id)
    await session.commit(); return m

async def update_badges(session,user_id:int):
    st=await session.get(UserStats,user_id)
    u=await session.get(User,user_id)
    if not st: return
    rate=st.correct/st.participations if st.participations else 0
    badges=[]
    if st.participations>=100 and rate>=.75: badges.append('🏆 Expert Sport')
    if st.participations>=250 and rate>=.80: badges.append('👑 Légende')
    if st.exact_scores>=10: badges.append('🎯 Tireur d’élite')
    if u and u.good_streak>=10: badges.append('🔥 En feu')
    if u and u.good_streak>=20: badges.append('⚡ Série légendaire')
    if st.participations>=25: badges.append('💬 Actif')
    if st.participations>=100: badges.append('📈 Régulier')
    if st.participations>=500: badges.append('🚀 Vétéran')
    for b in badges:
        if not await session.get(Badge, {'user_id':user_id,'badge':b}): session.add(Badge(user_id=user_id,badge=b))

async def ranking_text(session, limit=10):
    rows=(await session.execute(select(UserStats,User).join(User,User.id==UserStats.user_id).where(UserStats.participations>=settings.MIN_RANKING_PARTICIPATIONS).order_by(desc(UserStats.correct*1.0/UserStats.participations),desc(UserStats.participations),desc(UserStats.exact_scores)).limit(limit))).all()
    if not rows: return '🏆 TOP PRONOSTIQUEURS\n\nPas encore assez de participations.'
    lines=['🏆 TOP PRONOSTIQUEURS\n']
    medals=['🥇','🥈','🥉']
    for i,(st,u) in enumerate(rows):
        rate=round(st.correct*100/st.participations,1) if st.participations else 0
        b=(await session.execute(select(Badge.badge).where(Badge.user_id==st.user_id).limit(1))).scalar_one_or_none() or ''
        lines.append(f"{medals[i] if i<3 else '🏅'} {anonymize((u.first_name or u.username or str(u.id)))}\n📊 {rate}% de réussite\n📝 {st.participations} participations\n🎯 {st.exact_scores} scores exacts\n{b}\n")
    return '\n'.join(lines)
