import asyncio
from app.db import SessionLocal
from app.models.entities import User, Subscription, ProxyAccess
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        u=(await db.execute(select(User).where(User.telegram_id==1208301694))).scalar_one_or_none()
        print("user", u)
        if not u: return
        subs=(await db.execute(select(Subscription).where(Subscription.user_id==u.id))).scalars().all()
        for s in subs:
            print("sub", s.status, s.ends_at, s.marzban_username, getattr(s,"sub_token",None))
        proxy=(await db.execute(select(ProxyAccess).where(ProxyAccess.user_id==u.id))).scalar_one_or_none()
        print("proxy", None if not proxy else (proxy.status, proxy.ends_at))
asyncio.run(main())
