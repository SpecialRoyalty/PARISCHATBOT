from sqlalchemy import select, delete
from app.db.session import SessionLocal
from app.db.models import Role

async def roles_for(uid:int)->set[str]:
    async with SessionLocal() as s:
        res=await s.execute(select(Role.role).where(Role.user_id==uid))
        return set(res.scalars().all())
async def is_super(uid:int)->bool: return 'super_admin' in await roles_for(uid)
async def is_admin(uid:int)->bool:
    r=await roles_for(uid); return bool({'admin','super_admin'} & r)
async def is_trusted(uid:int)->bool:
    r=await roles_for(uid); return bool({'trusted','admin','super_admin'} & r)
async def add_role(uid:int, role:str):
    async with SessionLocal() as s:
        if not await s.get(Role, {'user_id':uid,'role':role}): s.add(Role(user_id=uid,role=role))
        await s.commit()
async def remove_role(uid:int, role:str):
    async with SessionLocal() as s:
        await s.execute(delete(Role).where(Role.user_id==uid, Role.role==role)); await s.commit()
