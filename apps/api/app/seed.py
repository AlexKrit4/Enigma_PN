from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models.entities import Plan, VpnNode

# New catalog. Old slugs are deactivated below.
PLANS = [
    # Ограниченный трафик — 1 месяц, 3 устройства, отключается по трафику или сроку
    {
        "slug": "limited-30gb",
        "name": "30 ГБ — 1 месяц",
        "group_name": "ограниченный",
        "duration_days": 30,
        "traffic_gb": 30,
        "device_limit": 3,
        "price_rub": "100.00",
        "sort_order": 10,
    },
    {
        "slug": "limited-100gb",
        "name": "100 ГБ — 1 месяц",
        "group_name": "ограниченный",
        "duration_days": 30,
        "traffic_gb": 100,
        "device_limit": 3,
        "price_rub": "300.00",
        "sort_order": 20,
    },
    {
        "slug": "limited-250gb",
        "name": "250 ГБ — 1 месяц",
        "group_name": "ограниченный",
        "duration_days": 30,
        "traffic_gb": 250,
        "device_limit": 3,
        "price_rub": "600.00",
        "sort_order": 30,
    },
    # Вечный трафик — лимит только по времени, 3 устройства
    {
        "slug": "eternal-1m",
        "name": "Вечный трафик — 1 месяц",
        "group_name": "вечный",
        "duration_days": 30,
        "traffic_gb": None,
        "device_limit": 3,
        "price_rub": "200.00",
        "sort_order": 40,
    },
    {
        "slug": "eternal-3m",
        "name": "Вечный трафик — 3 месяца",
        "group_name": "вечный",
        "duration_days": 90,
        "traffic_gb": None,
        "device_limit": 3,
        "price_rub": "500.00",
        "sort_order": 50,
    },
    {
        "slug": "eternal-6m",
        "name": "Вечный трафик — 6 месяцев",
        "group_name": "вечный",
        "duration_days": 180,
        "traffic_gb": None,
        "device_limit": 3,
        "price_rub": "800.00",
        "sort_order": 60,
    },
    # SOCKS5 прокси для Telegram — логин/пароль на аккаунт покупателя
    {
        "slug": "proxy-1m",
        "name": "SOCKS5 прокси — 1 месяц",
        "group_name": "прокси",
        "duration_days": 30,
        "traffic_gb": None,
        "device_limit": 1,
        "price_rub": "70.00",
        "sort_order": 70,
    },
]

ACTIVE_SLUGS = {p["slug"] for p in PLANS}


async def seed() -> None:
    settings = get_settings()
    async with SessionLocal() as db:
        for item in PLANS:
            existing = await db.execute(select(Plan).where(Plan.slug == item["slug"]))
            plan = existing.scalar_one_or_none()
            if plan:
                for k, v in item.items():
                    if k == "price_rub":
                        setattr(plan, k, Decimal(v))
                    else:
                        setattr(plan, k, v)
                plan.is_active = True
            else:
                db.add(
                    Plan(
                        slug=item["slug"],
                        name=item["name"],
                        group_name=item["group_name"],
                        duration_days=item["duration_days"],
                        traffic_gb=item["traffic_gb"],
                        device_limit=item["device_limit"],
                        price_rub=Decimal(item["price_rub"]),
                        sort_order=item["sort_order"],
                        is_active=True,
                    )
                )

        # Remove old sales catalog from the shop.
        old = await db.execute(select(Plan).where(Plan.slug.not_in(ACTIVE_SLUGS)))
        for plan in old.scalars().all():
            plan.is_active = False

        for node_cfg in settings.vpn_nodes:
            node_id = str(node_cfg["id"])
            node = await db.get(VpnNode, node_id)
            if not node:
                db.add(
                    VpnNode(
                        id=node_id,
                        name=str(node_cfg.get("name", node_id)),
                        weight=int(node_cfg.get("weight", 100)),
                        is_enabled=True,
                    )
                )
            else:
                node.name = str(node_cfg.get("name", node.name))
                node.weight = int(node_cfg.get("weight", node.weight))
                node.is_enabled = True

        await db.commit()
        print("Seed OK: new tariff catalog + vpn_nodes")


if __name__ == "__main__":
    asyncio.run(seed())
