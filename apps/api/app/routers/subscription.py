from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.models.entities import Order, Subscription, SubscriptionStatus
from app.services.happ import build_subscription_response
from app.services.marzban import MarzbanClient
from app.services.provisioning import mark_order_paid
from app.services.yoomoney import YooMoneyProvider

router = APIRouter(tags=["subscription", "webhooks"])


@router.get("/s/{sub_token}")
async def subscription_proxy(
    sub_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    # Simple rate limit via Redis
    redis: Redis = request.app.state.redis
    key = f"rl:sub:{sub_token}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > 60:
        raise HTTPException(status_code=429, detail="Too many requests")

    result = await db.execute(select(Subscription).where(Subscription.sub_token == sub_token))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub.status not in (SubscriptionStatus.trial, SubscriptionStatus.active):
        raise HTTPException(status_code=403, detail="Subscription inactive")

    cache_key = f"subcfg:{sub_token}"
    cached = await redis.get(cache_key)
    if cached:
        body = cached
        links: list[str] = []
    else:
        if not sub.marzban_username:
            raise HTTPException(status_code=503, detail="Not provisioned yet")
        marzban = MarzbanClient(settings)
        links = await marzban.get_subscription_links(sub.marzban_username)
        body, _ = build_subscription_response(sub, links, settings)
        await redis.setex(cache_key, 180, body)

    _, headers = build_subscription_response(sub, links if not cached else [], settings)
    return Response(content=body, media_type="text/plain; charset=utf-8", headers=headers)


@router.post("/webhooks/yoomoney")
async def yoomoney_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    provider = YooMoneyProvider(settings)
    form = await provider.parse_request(request)
    result = provider.verify_notification(form)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "invalid notification")

    order_result = await db.execute(select(Order).where(Order.payment_label == result.label))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for label")

    # Amount check (allow small float diffs)
    if result.amount < order.amount:
        raise HTTPException(status_code=400, detail="Amount too low")

    order, sub, created = await mark_order_paid(
        db,
        order=order,
        external_id=result.external_id,
        raw=result.raw,
        settings=settings,
    )
    return {
        "ok": True,
        "created": created,
        "order_id": str(order.id),
        "subscription_id": str(sub.id) if sub else None,
    }


@router.post("/pay/mock/{order_id}")
async def mock_pay(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Dev-only: simulate YooMoney payment when wallet is not configured."""
    if settings.yoomoney_wallet:
        raise HTTPException(status_code=403, detail="Mock pay disabled when YOOMONEY_WALLET is set")
    from uuid import UUID

    order = await db.get(Order, UUID(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order, sub, created = await mark_order_paid(
        db,
        order=order,
        external_id=f"mock-{order.payment_label}",
        raw={"mock": True, "label": order.payment_label},
        settings=settings,
    )
    return {
        "ok": True,
        "created": created,
        "order_id": str(order.id),
        "subscription_id": str(sub.id) if sub else None,
        "hint": "Откройте бота → Моя подписка",
    }


@router.get("/pay/mock/{order_id}")
async def mock_pay_page(order_id: str) -> Response:
    html = f"""<!doctype html><html><body style="font-family:sans-serif;padding:2rem">
    <h1>Mock оплата Enigma_PN</h1>
    <p>Заказ: <code>{order_id}</code></p>
    <form method="post"><button type="submit">Симулировать успешную оплату</button></form>
    </body></html>"""
    return Response(content=html, media_type="text/html")
