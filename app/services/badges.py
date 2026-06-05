from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.db.models import User, Badge

BADGE_RULES = [
    ('active', '💬 Actif', lambda u: u.total_predictions >= 25),
    ('regular', '📈 Régulier', lambda u: u.total_predictions >= 100),
    ('veteran', '🚀 Vétéran', lambda u: u.total_predictions >= 500),
    ('sharpshooter', '🎯 Tireur d’élite', lambda u: u.exact_scores >= 10),
    ('hot_streak', '🔥 En feu', lambda u: u.current_streak >= 10),
    ('legendary_streak', '⚡ Série légendaire', lambda u: u.current_streak >= 20),
    ('expert_sport', '🏆 Expert Sport', lambda u: u.total_predictions >= 100 and (u.good_predictions * 100 / max(u.total_predictions, 1)) >= 75),
    ('legend', '👑 Légende', lambda u: u.total_predictions >= 250 and (u.good_predictions * 100 / max(u.total_predictions, 1)) >= 80),
    ('ambassador_bronze', '🥉 Ambassadeur Bronze', lambda u: u.invite_count >= 5),
    ('ambassador_silver', '🥈 Ambassadeur Argent', lambda u: u.invite_count >= 25),
    ('ambassador_gold', '🥇 Ambassadeur Or', lambda u: u.invite_count >= 50),
]

async def award_badges_for_user(user_id: int) -> list[str]:
    awarded=[]
    async with SessionLocal() as s:
        u=await s.get(User, user_id)
        if not u:
            return awarded
        existing=set((await s.execute(select(Badge.code).where(Badge.user_id==user_id))).scalars().all())
        for code, label, pred in BADGE_RULES:
            if code not in existing and pred(u):
                s.add(Badge(user_id=user_id, code=code, label=label))
                awarded.append(label)
        if awarded:
            await s.commit()
    return awarded

async def award_badges_for_all() -> int:
    total=0
    async with SessionLocal() as s:
        ids=(await s.execute(select(User.id))).scalars().all()
    for uid in ids:
        total += len(await award_badges_for_user(uid))
    return total

async def badge_health() -> dict:
    await award_badges_for_all()
    async with SessionLocal() as s:
        users=(await s.execute(select(func.count(User.id)))).scalar() or 0
        badges=(await s.execute(select(func.count(Badge.id)))).scalar() or 0
        eligible_active=(await s.execute(select(func.count(User.id)).where(User.total_predictions>=25))).scalar() or 0
        eligible_exact=(await s.execute(select(func.count(User.id)).where(User.exact_scores>=10))).scalar() or 0
        eligible_invite=(await s.execute(select(func.count(User.id)).where(User.invite_count>=5))).scalar() or 0
    return {
        'users': users,
        'badges': badges,
        'eligible_active': eligible_active,
        'eligible_exact': eligible_exact,
        'eligible_invite': eligible_invite,
        'status': '✅ OK'
    }

async def user_badges(user_id:int) -> list[Badge]:
    async with SessionLocal() as s:
        return (await s.execute(select(Badge).where(Badge.user_id==user_id).order_by(Badge.created_at))).scalars().all()
