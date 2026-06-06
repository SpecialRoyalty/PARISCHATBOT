from datetime import datetime
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.db.models import Match, Prediction, User, ResultPrompt, SecurityLog
from app.config import settings
from app.utils.text import parse_title, anonymize
from app.services.badges import award_badges_for_user

def fmt_dt(dt): return dt.strftime('%d/%m/%Y à %H:%M') if dt else 'Non définie'

async def create_match(category,title,photo_file_id,start_at,end_at,created_by,status='active',proposed_by=None):
    a,b=parse_title(title)
    async with SessionLocal() as s:
        m=Match(category=category,title=title,team_a=a,team_b=b,photo_file_id=photo_file_id,start_at=start_at,end_at=end_at,created_by=created_by,status=status,proposed_by=proposed_by)
        s.add(m); await s.commit(); await s.refresh(m); return m

async def get_match(mid:int):
    async with SessionLocal() as s: return await s.get(Match,mid)
async def active_matches():
    async with SessionLocal() as s:
        res=await s.execute(select(Match).where(Match.status=='active').order_by(Match.start_at)); return res.scalars().all()
async def closed_matches(limit=10):
    async with SessionLocal() as s:
        res=await s.execute(select(Match).where(Match.status.in_(['closed','cancelled'])).order_by(Match.id.desc()).limit(limit)); return res.scalars().all()
async def pending_matches():
    async with SessionLocal() as s:
        res=await s.execute(select(Match).where(Match.status=='pending').order_by(Match.id.desc())); return res.scalars().all()

async def match_stats(mid:int):
    async with SessionLocal() as s:
        total=(await s.execute(select(func.count(Prediction.id)).where(Prediction.match_id==mid))).scalar() or 0
        counts={}
        for w in ['a','b','draw']:
            counts[w]=(await s.execute(select(func.count(Prediction.id)).where(Prediction.match_id==mid, Prediction.winner==w))).scalar() or 0
        top10=(await s.execute(select(User.id).where(User.total_predictions>=10).order_by((User.good_predictions*1.0/User.total_predictions).desc(), User.total_predictions.desc()).limit(10))).scalars().all()
        top_voted=(await s.execute(select(func.count(Prediction.id)).where(Prediction.match_id==mid, Prediction.user_id.in_(top10)))).scalar() if top10 else 0
        return {'total':total,'a':counts['a'],'b':counts['b'],'draw':counts['draw'],'pa': round(counts['a']*100/total) if total else 0,'pb':round(counts['b']*100/total) if total else 0,'pd':round(counts['draw']*100/total) if total else 0,'top10':top_voted or 0}

async def render_match_message(m:Match):
    st=await match_stats(m.id)
    return (f"🏟 {m.title}\n\n"
            f"📅 Début : {fmt_dt(m.start_at)}\n"
            f"🏁 Fin approx. : {fmt_dt(m.end_at)}\n"
            f"🏆 Catégorie : {m.category}\n\n"
            f"👥 {st['total']} participants\n\n"
            f"{m.team_a} : {st['pa']}%\n"
            f"{m.team_b} : {st['pb']}%\n"
            f"🤝 Match nul : {st['pd']}%\n\n"
            f"🔥 {st['top10']} membres du Top 10 ont déjà pronostiqué\n\n"
            f"⚡ Faites votre pronostic avant le début du match !\n\n"
            f"👇 Donne ton pronostic")

async def save_vote(mid:int, user_id:int, winner:str, exact_score:str|None):
    async with SessionLocal() as s:
        m=await s.get(Match,mid)
        if not m or m.status!='active' or datetime.utcnow()>=m.start_at:
            return False,'closed'
        p=Prediction(match_id=mid,user_id=user_id,winner=winner,exact_score=exact_score)
        s.add(p)
        try:
            u=await s.get(User,user_id)
            if u: u.total_predictions += 1
            await s.commit(); return True,'ok'
        except IntegrityError:
            await s.rollback(); return False,'duplicate'

async def lock_started_matches(bot):
    async with SessionLocal() as s:
        res=await s.execute(select(Match).where(Match.status=='active', Match.start_at<=datetime.utcnow()))
        for m in res.scalars().all():
            m.status='locked'
            if m.group_message_id:
                try: await bot.delete_message(settings.GROUP_ID,m.group_message_id)
                except Exception: pass
        await s.commit()

async def matches_to_close():
    async with SessionLocal() as s:
        res=await s.execute(select(Match).where(Match.status=='locked', Match.end_at!=None, Match.end_at<=datetime.utcnow()))
        return res.scalars().all()

async def delete_result_prompts(bot, mid:int):
    async with SessionLocal() as s:
        prompts=(await s.execute(select(ResultPrompt).where(ResultPrompt.match_id==mid))).scalars().all()
        for p in prompts:
            try:
                await bot.delete_message(p.user_id, p.message_id)
            except Exception:
                pass
            await s.delete(p)
        await s.commit()

async def register_result_prompt(mid:int, user_id:int, message_id:int):
    async with SessionLocal() as s:
        exists=(await s.execute(select(ResultPrompt).where(ResultPrompt.match_id==mid, ResultPrompt.user_id==user_id))).scalar_one_or_none()
        if exists:
            return False
        s.add(ResultPrompt(match_id=mid, user_id=user_id, message_id=message_id))
        await s.commit()
        return True

async def result_prompt_exists(mid:int):
    async with SessionLocal() as s:
        return (await s.execute(select(func.count(ResultPrompt.id)).where(ResultPrompt.match_id==mid))).scalar() or 0

async def close_match(mid:int, winner:str, score:str|None):
    async with SessionLocal() as s:
        m=await s.get(Match,mid)
        if not m: return None
        m.status='closed'; m.result_winner=winner; m.result_score=score
        preds=(await s.execute(select(Prediction).where(Prediction.match_id==mid))).scalars().all()
        for p in preds:
            good=(p.winner==winner)
            exact=bool(score and p.exact_score==score)
            p.is_good=good; p.is_exact=exact
            u=await s.get(User,p.user_id)
            if u:
                if good: u.good_predictions += 1; u.current_streak += 1
                else: u.current_streak = 0
                if exact: u.exact_scores += 1
        affected_user_ids=list({p.user_id for p in preds})
        await s.commit()
    for uid in affected_user_ids:
        await award_badges_for_user(uid)
    return m
