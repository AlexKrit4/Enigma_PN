from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import create_access_token, get_current_user
from app.models.entities import Order, OrderStatus, Plan, User
from app.schemas import SiteDevicesOrderIn, SiteLoginIn, SiteOrderIn, SiteRegisterIn
from app.services.provisioning import (
    create_order,
    create_trial,
    get_active_subscription,
    serialize_subscription_with_devices,
)
from app.services.site_pricing import (
    SITE_BASE_DEVICES,
    SITE_PLAN_SLUG,
    SITE_TRIAL_DAYS,
    pricing_catalog,
    quote_extra_devices,
    quote_subscription,
    to_money,
)
from app.services.yoomoney import YooMoneyProvider

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/site", tags=["site"])

def _truncate_password(password: str) -> bytes:
    """bcrypt accepts at most 72 bytes; truncate consistently for hash and verify."""
    return password.encode("utf-8")[:72]


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(_truncate_password(password), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate_password(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _order_payload(order: Order, payment_url: str | None = None) -> dict:
    meta = order.meta or {}
    return {
        "id": str(order.id),
        "status": order.status.value,
        "amount": str(order.amount),
        "currency": order.currency,
        "payment_label": order.payment_label,
        "payment_url": payment_url,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "title": meta.get("title"),
        "meta": meta,
    }


async def _me_payload(db: AsyncSession, user: User, settings: Settings) -> dict:
    sub = await get_active_subscription(db, user.id)
    return {
        "id": str(user.id),
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "subscription": await serialize_subscription_with_devices(
            db, sub, settings, include_devices=True
        ),
    }


async def _site_plan(db: AsyncSession) -> Plan | None:
    result = await db.execute(
        select(Plan).where(Plan.slug == SITE_PLAN_SLUG, Plan.is_active.is_(True))
    )
    return result.scalar_one_or_none()


@router.get("/pricing")
async def site_pricing() -> dict:
    return pricing_catalog()


@router.post("/orders/quote")
async def site_quote(body: SiteOrderIn) -> dict:
    try:
        return quote_subscription(body.months, body.extra_devices)
    except ValueError:
        raise HTTPException(status_code=400, detail="Проверьте параметры заказа")


@router.post("/register")
async def site_register(
    body: SiteRegisterIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user and user.password_hash:
        raise HTTPException(status_code=409, detail="Этот email уже зарегистрирован. Войдите в аккаунт.")
    if not user:
        user = User(email=email)
        db.add(user)
    user.password_hash = _hash_password(body.password)
    await db.flush()

    await create_trial(
        db,
        user,
        settings,
        traffic_gb=None,
        device_limit=SITE_BASE_DEVICES,
        duration_days=SITE_TRIAL_DAYS,
    )
    await db.commit()
    await db.refresh(user)
    log.info("site_user_registered", user_id=str(user.id))
    return {
        "access_token": create_access_token(user.id, settings),
        "user": await _me_payload(db, user, settings),
    }


@router.post("/login")
async def site_login(
    body: SiteLoginIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return {
        "access_token": create_access_token(user.id, settings),
        "user": await _me_payload(db, user, settings),
    }


@router.get("/me")
async def site_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return await _me_payload(db, user, settings)


@router.post("/logout")
async def site_logout() -> dict:
    return {"ok": True}


@router.post("/orders")
async def site_create_order(
    body: SiteOrderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        quote = quote_subscription(body.months, body.extra_devices)
    except ValueError:
        raise HTTPException(status_code=400, detail="Проверьте параметры заказа")
    plan = await _site_plan(db)
    if not plan:
        raise HTTPException(status_code=500, detail="Тариф временно недоступен")
    order = await create_order(
        db,
        user,
        plan,
        amount=to_money(quote["total"]),
        meta_extra={
            "duration_days": quote["days"],
            "traffic_gb": None,
            "device_limit": quote["devices"],
            "title": quote["title"],
        },
    )
    provider = YooMoneyProvider(settings)
    redirect = provider.create_payment(order, description=f"{settings.brand_name}: {quote['title']}")
    return _order_payload(order, redirect.payment_url)


@router.post("/orders/devices/quote")
async def site_devices_quote(
    body: SiteDevicesOrderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    sub = await get_active_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=400, detail="Нет активной подписки")
    try:
        return quote_extra_devices(body.extra_devices, sub.device_limit, sub.ends_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="Проверьте параметры заказа")


@router.post("/orders/devices")
async def site_create_devices_order(
    body: SiteDevicesOrderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    sub = await get_active_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=400, detail="Нет активной подписки")
    try:
        quote = quote_extra_devices(body.extra_devices, sub.device_limit, sub.ends_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="Проверьте параметры заказа")

    now = datetime.now(timezone.utc)
    remaining_days = max(1, ceil((sub.ends_at - now).total_seconds() / 86400))
    order = await create_order(
        db,
        user,
        None,
        amount=to_money(quote["total"]),
        duration_days=remaining_days,
        traffic_gb=None,
        device_limit=quote["devices"],
        title=quote["title"],
        kind="свой",
    )
    provider = YooMoneyProvider(settings)
    redirect = provider.create_payment(order, description=f"{settings.brand_name}: {quote['title']}")
    return _order_payload(order, redirect.payment_url)


@router.get("/orders")
async def site_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(20)
    )
    provider = YooMoneyProvider(settings)
    payload = []
    for order in result.scalars():
        payment_url = None
        if order.status == OrderStatus.pending:
            redirect = provider.create_payment(
                order, description=f"{settings.brand_name}: {(order.meta or {}).get('title') or 'VPN'}"
            )
            payment_url = redirect.payment_url
        payload.append(_order_payload(order, payment_url))
    return payload


@router.get("/orders/{order_id}")
async def site_order_status(
    order_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    payment_url = None
    if order.status == OrderStatus.pending:
        provider = YooMoneyProvider(settings)
        redirect = provider.create_payment(
            order, description=f"{settings.brand_name}: {(order.meta or {}).get('title') or 'VPN'}"
        )
        payment_url = redirect.payment_url
    return _order_payload(order, payment_url)
