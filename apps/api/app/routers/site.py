from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from math import ceil
import secrets
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import create_access_token, get_current_user, require_admin
from app.models.entities import (
    Order,
    OrderStatus,
    Plan,
    Subscription,
    SubscriptionDevice,
    SubscriptionStatus,
    User,
)
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
        "is_admin": bool(user.is_admin),
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


# ── Hidden site admin (is_admin flag, same site JWT) ──────────────────────────

@router.get("/admin/overview")
async def site_admin_overview(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    site_users = await db.scalar(select(func.count(User.id)).where(User.email.isnot(None)))
    verified = await db.scalar(
        select(func.count(User.id)).where(User.email.isnot(None), User.email_verified.is_(True))
    )
    new_7d = await db.scalar(
        select(func.count(User.id)).where(User.email.isnot(None), User.created_at >= week_ago)
    )
    new_30d = await db.scalar(
        select(func.count(User.id)).where(User.email.isnot(None), User.created_at >= month_ago)
    )
    bot_users = await db.scalar(select(func.count(User.id)).where(User.telegram_id.isnot(None)))

    active_filter = [
        Subscription.status.in_([SubscriptionStatus.trial, SubscriptionStatus.active]),
        Subscription.ends_at > now,
    ]
    active_subs = await db.scalar(select(func.count(Subscription.id)).where(*active_filter))
    trial_subs = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.trial, Subscription.ends_at > now
        )
    )
    paid_subs = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.active, Subscription.ends_at > now
        )
    )
    expiring_3d = await db.scalar(
        select(func.count(Subscription.id)).where(
            *active_filter, Subscription.ends_at <= now + timedelta(days=3)
        )
    )

    paid_count, paid_sum = (
        await db.execute(
            select(func.count(Order.id), func.coalesce(func.sum(Order.amount), 0)).where(
                Order.status == OrderStatus.paid
            )
        )
    ).one()
    paid_count = paid_count or 0
    revenue_7d = await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status == OrderStatus.paid, Order.paid_at >= week_ago
        )
    )
    revenue_30d = await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status == OrderStatus.paid, Order.paid_at >= month_ago
        )
    )
    pending = await db.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.pending)
    )
    failed = await db.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.failed)
    )
    paying_users = await db.scalar(
        select(func.count(func.distinct(Order.user_id))).where(Order.status == OrderStatus.paid)
    )
    paying_site_users = await db.scalar(
        select(func.count(func.distinct(Order.user_id)))
        .join(User, Order.user_id == User.id)
        .where(Order.status == OrderStatus.paid, User.email.isnot(None))
    )
    site_users_with_sub = await db.scalar(
        select(func.count(func.distinct(Subscription.user_id)))
        .join(User, Subscription.user_id == User.id)
        .where(User.email.isnot(None), *active_filter)
    )

    day_col = func.date_trunc("day", Order.paid_at).label("d")
    daily_rows = (
        await db.execute(
            select(day_col, func.sum(Order.amount))
            .where(Order.status == OrderStatus.paid, Order.paid_at >= month_ago)
            .group_by(day_col)
            .order_by(day_col)
        )
    ).all()
    revenue_daily = [
        {"day": d.date().isoformat(), "amount": str(total)} for d, total in daily_rows
    ]

    return {
        "users_site": site_users or 0,
        "users_verified": verified or 0,
        "users_bot": bot_users or 0,
        "users_new_7d": new_7d or 0,
        "users_new_30d": new_30d or 0,
        "site_users_with_sub": site_users_with_sub or 0,
        "paying_site_users": paying_site_users or 0,
        "subscriptions_active": active_subs or 0,
        "subscriptions_trial": trial_subs or 0,
        "subscriptions_paid": paid_subs or 0,
        "subscriptions_expiring_3d": expiring_3d or 0,
        "orders_paid": paid_count,
        "orders_pending": pending or 0,
        "orders_failed": failed or 0,
        "paying_users": paying_users or 0,
        "revenue_rub": str(paid_sum or 0),
        "revenue_7d": str(revenue_7d or 0),
        "revenue_30d": str(revenue_30d or 0),
        "avg_check": str(round((paid_sum or 0) / paid_count, 2)) if paid_count else "0",
        "revenue_daily": revenue_daily,
    }


@router.get("/admin/users")
async def site_admin_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(User).where(User.email.isnot(None)).order_by(User.created_at.desc()).limit(500)
    )
    users = result.scalars().all()
    if not users:
        return []
    user_ids = [u.id for u in users]
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id.in_(user_ids),
            Subscription.status.in_([SubscriptionStatus.trial, SubscriptionStatus.active]),
            Subscription.ends_at > now,
        )
    )
    subs: dict[UUID, Subscription] = {}
    for s in sub_result.scalars():
        if s.user_id not in subs or s.ends_at > subs[s.user_id].ends_at:
            subs[s.user_id] = s
    sub_ids = [s.id for s in subs.values()]
    device_counts: dict[UUID, int] = {}
    if sub_ids:
        for sid, cnt in await db.execute(
            select(SubscriptionDevice.subscription_id, func.count())
            .where(SubscriptionDevice.subscription_id.in_(sub_ids))
            .group_by(SubscriptionDevice.subscription_id)
        ):
            device_counts[sid] = cnt
    paid_stats: dict[UUID, tuple[int, float]] = {}
    for uid, cnt, total in await db.execute(
        select(Order.user_id, func.count(), func.coalesce(func.sum(Order.amount), 0))
        .where(Order.user_id.in_(user_ids), Order.status == OrderStatus.paid)
        .group_by(Order.user_id)
    ):
        paid_stats[uid] = (cnt, float(total))
    last_sub_ends: dict[UUID, datetime] = {}
    for uid, ends in await db.execute(
        select(Subscription.user_id, func.max(Subscription.ends_at))
        .where(Subscription.user_id.in_(user_ids))
        .group_by(Subscription.user_id)
    ):
        last_sub_ends[uid] = ends
    payload = []
    for u in users:
        s = subs.get(u.id)
        paid_cnt, paid_total = paid_stats.get(u.id, (0, 0.0))
        payload.append(
            {
                "id": str(u.id),
                "email": u.email,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "email_verified": bool(u.email_verified),
                "is_admin": bool(u.is_admin),
                "telegram_linked": bool(u.telegram_id),
                "orders_paid": paid_cnt,
                "total_paid": str(paid_total),
                "last_sub_ends_at": (
                    last_sub_ends[u.id].isoformat() if u.id in last_sub_ends else None
                ),
                "subscription": (
                    {
                        "status": s.status.value,
                        "ends_at": s.ends_at.isoformat(),
                        "device_limit": s.device_limit,
                        "devices_connected": device_counts.get(s.id, 0),
                        "traffic_used_gb": str(s.traffic_used_gb),
                        "days_left": max(0, ceil((s.ends_at - now).total_seconds() / 86400)),
                    }
                    if s
                    else None
                ),
            }
        )
    return payload


@router.get("/admin/payments")
async def site_admin_payments(
    status: str = "paid",
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    try:
        order_status = OrderStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown order status")
    result = await db.execute(
        select(Order, User.email, User.telegram_id, User.username)
        .join(User, Order.user_id == User.id)
        .where(Order.status == order_status)
        .order_by(Order.paid_at.desc().nullslast(), Order.created_at.desc())
        .limit(300)
    )
    payload = []
    for order, email, telegram_id, username in result.all():
        meta = order.meta or {}
        if email:
            user_label = email
        elif username:
            user_label = f"@{username}"
        elif telegram_id:
            user_label = f"tg:{telegram_id}"
        else:
            user_label = str(order.user_id)
        payload.append(
            {
                "id": str(order.id),
                "user": user_label,
                "email": email,
                "amount": str(order.amount),
                "currency": order.currency,
                "status": order.status.value,
                "title": meta.get("title"),
                "kind": meta.get("kind"),
                "duration_days": meta.get("duration_days"),
                "device_limit": meta.get("device_limit"),
                "provider": order.payment_provider,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            }
        )
    return payload
