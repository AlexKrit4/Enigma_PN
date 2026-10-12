from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from math import ceil
import secrets
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import create_access_token, get_current_user
from app.models.entities import Order, OrderStatus, Plan, User
from app.schemas import (
    SiteDevicesOrderIn,
    SiteLoginIn,
    SiteOrderIn,
    SiteRegisterIn,
    SiteResendIn,
    SiteVerifyIn,
)
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
from app.services.emailer import send_verification_code
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


CODE_TTL = 600
CODE_MAX_TRIES = 10
RESEND_COOLDOWN = 60


def _verify_key(email: str) -> str:
    return f"site_verify:{email}"


def _tries_key(email: str) -> str:
    return f"site_verify_tries:{email}"


def _cooldown_key(email: str) -> str:
    return f"site_verify_cd:{email}"


async def _issue_code(redis, email: str, settings: Settings) -> bool:
    """Сгенерировать и отправить код. False, если действует кулдаун на переотправку."""
    if await redis.exists(_cooldown_key(email)):
        return False
    code = f"{secrets.randbelow(1_000_000):06d}"
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    pipe = redis.pipeline()
    pipe.set(_verify_key(email), digest, ex=CODE_TTL)
    pipe.set(_tries_key(email), 0, ex=CODE_TTL)
    pipe.set(_cooldown_key(email), 1, ex=RESEND_COOLDOWN)
    await pipe.execute()
    try:
        await send_verification_code(email, code, settings)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Не удалось отправить письмо с кодом. Попробуйте через пару минут.",
        )
    return True


async def _check_code(redis, email: str, code: str) -> bool:
    digest = await redis.get(_verify_key(email))
    if not digest:
        return False
    tries = int(await redis.get(_tries_key(email)) or 0)
    if tries >= CODE_MAX_TRIES:
        return False
    await redis.incr(_tries_key(email))
    ok = hashlib.sha256(code.strip().encode("utf-8")).hexdigest() == digest
    if ok:
        await redis.delete(_verify_key(email), _tries_key(email))
    return ok


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
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user and user.password_hash and user.email_verified:
        raise HTTPException(status_code=409, detail="Этот email уже зарегистрирован. Войдите в аккаунт.")
    if not user:
        user = User(email=email)
        db.add(user)
    user.password_hash = _hash_password(body.password)
    user.email_verified = False
    await db.commit()

    await _issue_code(request.app.state.redis, email, settings)
    log.info("site_user_registered_pending", user_id=str(user.id))
    return {"status": "pending_verification", "email": email}


@router.post("/verify")
async def site_verify(
    body: SiteVerifyIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    email = body.email.strip().lower()
    if not await _check_code(request.app.state.redis, email, body.code):
        raise HTTPException(status_code=400, detail="Неверный или просроченный код. Запросите новый.")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="Сначала зарегистрируйтесь.")
    user.email_verified = True

    if not await get_active_subscription(db, user.id):
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
    log.info("site_user_verified", user_id=str(user.id))
    return {
        "access_token": create_access_token(user.id, settings),
        "user": await _me_payload(db, user, settings),
    }


@router.post("/resend")
async def site_resend_code(
    body: SiteResendIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user and user.password_hash and not user.email_verified:
        sent = await _issue_code(request.app.state.redis, email, settings)
        if not sent:
            raise HTTPException(status_code=429, detail="Код уже отправлен. Подождите минуту и запросите новый.")
    return {"ok": True, "cooldown": RESEND_COOLDOWN}


@router.post("/login")
async def site_login(
    body: SiteLoginIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    if not user.email_verified:
        await _issue_code(request.app.state.redis, email, settings)
        raise HTTPException(status_code=403, detail="Подтвердите email — мы отправили вам код.")
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
