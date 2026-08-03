from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.db import SessionLocal
from app.services.marzban import MarzbanClient
from app.services.provisioning import expire_due_subscriptions


async def startup(ctx: dict) -> None:
    ctx["settings"] = get_settings()


async def expire_subscriptions(ctx: dict) -> int:
    async with SessionLocal() as db:
        return await expire_due_subscriptions(db, ctx["settings"])


async def health_check_nodes(ctx: dict) -> bool:
    client = MarzbanClient(ctx["settings"])
    return await client.health()


class WorkerSettings:
    functions = [expire_subscriptions, health_check_nodes]
    cron_jobs = [
        cron(expire_subscriptions, minute={0, 15, 30, 45}),
        cron(health_check_nodes, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
