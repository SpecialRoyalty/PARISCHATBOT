from app.db.session import SessionLocal
from app.db.models import Setting
from datetime import datetime

DEFAULT_START='Bienvenue dans le bot Pronostic Sport. Ici tu peux consulter les pronostics en cours, donner ton avis et participer aux classements du groupe.'
DEFAULT_RULES='🏆 RÈGLES DU GROUPE SPORT 🏆\n\n✅ Discutez librement de sport.\n✅ Proposez des matchs.\n❌ Liens interdits.\n❌ Spam, scam, insultes et commandes interdites.\n🤝 Respect obligatoire.'
async def get_setting(key:str, default:str|None=None):
    async with SessionLocal() as s:
        x=await s.get(Setting,key)
        return x.value if x and x.value is not None else default
async def set_setting(key:str, value:str|None):
    async with SessionLocal() as s:
        x=await s.get(Setting,key)
        if not x: s.add(Setting(key=key,value=value,updated_at=datetime.utcnow()))
        else: x.value=value; x.updated_at=datetime.utcnow()
        await s.commit()
