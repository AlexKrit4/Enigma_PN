from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models.entities import Plan, VpnNode
from app.config import get_settings

PLANS = [
    # для себя
    {"slug": "self-1m", "name": "Для себя — 1 месяц", "group_name": "для себя", "duration_days": 30, "traffic_gb": 50, "device_limit": 2, "price_rub": "100.00", "sort_order": 10},
    {"slug": "self-3m", "name": "Для себя — 3 месяца", "group_name": "для себя", "duration_days": 90, "traffic_gb": 150, "device_limit": 2, "price_rub": "299.00", "sort_order": 20},
    {"slug": "self-1y", "name": "Для себя — 1 год", "group_name": "для себя", "duration_days": 365, "traffic_gb": 700, "device_limit": 2, "price_rub": "999.00", "sort_order": 30},
    # семейный
    {"slug": "family-1m", "name": "Семейный — 1 месяц", "group_name": "семейный", "duration_days": 30, "traffic_gb": 100, "device_limit": 4, "price_rub": "225.00", "sort_order": 40},
    {"slug": "family-3m", "name": "Семейный — 3 месяца", "group_name": "семейный", "duration_days": 90, "traffic_gb": 300, "device_limit": 4, "price_rub": "649.00", "sort_order": 50},
    {"slug": "family-1y", "name": "Семейный — 1 год", "group_name": "семейный", "duration_days": 365, "traffic_gb": 1300, "device_limit": 4, "price_rub": "2249.00", "sort_order": 60},
]


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
        print("Seed OK: plans + vpn_nodes")


if __name__ == "__main__":
    asyncio.run(seed())
