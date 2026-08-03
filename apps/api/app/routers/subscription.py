from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models.entities import Order, Subscription, SubscriptionStatus, User
from app.services.devices import (
    active_device_count,
    kick_device,
    list_devices,
    serialize_device,
    touch_device,
)
from app.services.happ import (
    announce_header,
    build_happ_redirect_html,
    build_sub_status_text,
    build_sub_url,
    build_subscription_response,
)
from app.services.marzban import MarzbanClient
from app.services.provisioning import (
    get_active_subscription,
    mark_order_paid,
    notify_subscription_ready,
    serialize_subscription_with_devices,
)
from app.services.yoomoney import YooMoneyProvider

log = structlog.get_logger(__name__)

router = APIRouter(tags=["subscription", "webhooks"])


def _header_first(request: Request, *names: str) -> str | None:
    for name in names:
        value = request.headers.get(name)
        if value and value.strip():
            return value.strip()
    return None


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

    hwid = _header_first(request, "x-hwid", "x-device-id", "hwid")
    device_os = _header_first(request, "x-device-os", "x-os")
    device_model = _header_first(request, "x-ver-os", "x-device-model", "x-model")
    user_agent = request.headers.get("user-agent")

    if hwid:
        _, err = await touch_device(
            db,
            subscription=sub,
            hwid=hwid,
            device_os=device_os,
            device_model=device_model,
            user_agent=user_agent,
        )
        if err == "blocked":
            msg = "Устройство отключено. Удалите его в боте или подключите другое."
            return Response(
                content="",
                status_code=403,
                media_type="text/plain; charset=utf-8",
                headers={
                    "announce": announce_header(msg),
                    "sub-info-text": msg[:200],
                    "sub-info-color": "red",
                    "subscription-always-hwid-enable": "1",
                },
            )
        if err == "limit_reached":
            used = await active_device_count(db, sub.id)
            msg = f"Лимит устройств {used}/{sub.device_limit}. Отключите лишнее в боте «Моя подписка»."
            return Response(
                content="",
                status_code=403,
                media_type="text/plain; charset=utf-8",
                headers={
                    "announce": announce_header(msg),
                    "sub-info-text": msg[:200],
                    "sub-info-color": "red",
                    "subscription-always-hwid-enable": "1",
                },
            )

    devices_used = await active_device_count(db, sub.id)
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
        body, _ = build_subscription_response(sub, links, settings, devices_used=devices_used)
        await redis.setex(cache_key, 180, body)

    _, headers = build_subscription_response(
        sub, links if not cached else [], settings, devices_used=devices_used
    )
    # Fresh status text even when body is cached.
    status_text = build_sub_status_text(sub, devices_used=devices_used)
    headers["announce"] = announce_header(status_text)
    headers["sub-info-text"] = status_text[:200]
    return Response(content=body, media_type="text/plain; charset=utf-8", headers=headers)


@router.get("/add/{sub_token}")
async def happ_add_redirect(
    sub_token: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """HTTPS bridge for Telegram buttons → opens Happ and imports subscription."""
    result = await db.execute(select(Subscription).where(Subscription.sub_token == sub_token))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub.status not in (SubscriptionStatus.trial, SubscriptionStatus.active):
        raise HTTPException(status_code=403, detail="Subscription inactive")
    sub_url = build_sub_url(sub_token, settings)
    html = build_happ_redirect_html(sub_url, brand=settings.brand_name)
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/api/v1/me/devices")
async def my_devices(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    sub = await get_active_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    devices = [serialize_device(d) for d in await list_devices(db, sub.id) if not d.is_blocked]
    return {
        "subscription_id": str(sub.id),
        "device_limit": sub.device_limit,
        "devices_used": len(devices),
        "devices": devices,
        "subscription": await serialize_subscription_with_devices(
            db, sub, settings, include_devices=True
        ),
    }


@router.delete("/api/v1/me/devices/{device_id}")
async def kick_my_device(
    device_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    sub = await get_active_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    device = await kick_device(db, subscription_id=sub.id, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    used = await active_device_count(db, sub.id)
    return {
        "ok": True,
        "kicked_id": str(device_id),
        "devices_used": used,
        "device_limit": sub.device_limit,
    }


@router.post("/api/v1/me/devices/{device_id}/kick")
async def kick_my_device_post(
    device_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """POST alias for bots that prefer POST over DELETE."""
    return await kick_my_device(device_id, user, db)


@router.post("/webhooks/yoomoney")
async def yoomoney_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    provider = YooMoneyProvider(settings)
    form = await provider.parse_request(request)
    log.info(
        "yoomoney_webhook_received",
        keys=sorted(form.keys()),
        label=form.get("label"),
        operation_id=form.get("operation_id"),
        amount=form.get("amount"),
        has_sign=bool(form.get("sign")),
        has_sha1=bool(form.get("sha1_hash")),
    )
    result = provider.verify_notification(form)
    if not result.success:
        log.warning("yoomoney_webhook_rejected", error=result.error, label=result.label)
        raise HTTPException(status_code=400, detail=result.error or "invalid notification")

    order_result = await db.execute(select(Order).where(Order.payment_label == result.label))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for label")

    # Amount check: accept withdraw_amount / credited amount with small fee slack
    if result.amount + Decimal("5.00") < order.amount:
        raise HTTPException(status_code=400, detail="Amount too low")

    order, sub, created = await mark_order_paid(
        db,
        order=order,
        external_id=result.external_id,
        raw=result.raw,
        settings=settings,
    )
    if created and sub:
        user = await db.get(User, order.user_id)
        if user:
            await notify_subscription_ready(
                db,
                user=user,
                sub=sub,
                title="Оплата получена — подписка активна",
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
    from uuid import UUID as _UUID

    order = await db.get(Order, _UUID(order_id))
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
