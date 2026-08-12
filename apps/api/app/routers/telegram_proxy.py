from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_or_create_telegram_user, require_bot
from app.schemas import TrialCreateIn
from app.services.provisioning import get_active_subscription
from app.services.telegram_proxy import build_telegram_proxy_links

router = APIRouter(prefix="/api/v1", tags=["telegram-proxy"])


class TelegramProxyOut(BaseModel):
    enabled: bool
    ready: bool
    host: str | None = None
    port: int | None = None
    tg_url: str | None = None
    https_url: str | None = None
    message: str
    subscription_required: bool = True
    has_active_subscription: bool = False


@router.post("/telegram-proxy", response_model=TelegramProxyOut)
async def get_telegram_proxy(
    body: TrialCreateIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_bot),
) -> TelegramProxyOut:
    """Return shared MTProto proxy links for users with an active subscription."""
    user = await get_or_create_telegram_user(db, body.telegram_id, body.username, settings)
    await db.commit()
    sub = await get_active_subscription(db, user.id)
    links = build_telegram_proxy_links(settings)

    if not sub:
        return TelegramProxyOut(
            enabled=links.enabled,
            ready=False,
            host=links.host or None,
            port=links.port,
            message="Нужна активная подписка (или пробный период).",
            subscription_required=True,
            has_active_subscription=False,
        )

    if not links.ready:
        return TelegramProxyOut(
            enabled=links.enabled,
            ready=False,
            host=links.host or None,
            port=links.port,
            message=links.message,
            subscription_required=True,
            has_active_subscription=True,
        )

    return TelegramProxyOut(
        enabled=True,
        ready=True,
        host=links.host,
        port=links.port,
        tg_url=links.tg_url,
        https_url=links.https_url,
        message="OK",
        subscription_required=True,
        has_active_subscription=True,
    )


@router.get("/telegram-proxy/public-info", response_model=TelegramProxyOut)
async def telegram_proxy_public_info(settings: Settings = Depends(get_settings)) -> TelegramProxyOut:
    """Public status without exposing the secret."""
    links = build_telegram_proxy_links(settings)
    if not links.enabled:
        return TelegramProxyOut(enabled=False, ready=False, message=links.message)
    if not links.ready:
        return TelegramProxyOut(
            enabled=True,
            ready=False,
            host=links.host or None,
            port=links.port,
            message="Прокси настраивается.",
        )
    return TelegramProxyOut(
        enabled=True,
        ready=True,
        host=links.host,
        port=links.port,
        message="Прокси доступен подписчикам через бота.",
    )
