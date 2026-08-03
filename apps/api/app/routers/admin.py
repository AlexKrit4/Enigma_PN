from __future__ import annotations

import asyncio
import csv
import io
import os
import secrets
import shutil
import socket
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from jose import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_or_create_telegram_user, require_admin_api
from app.models.entities import (
    Order,
    OrderStatus,
    Plan,
    PromoCode,
    Subscription,
    SubscriptionStatus,
    User,
)
from app.schemas import (
    AdminBroadcastIn,
    AdminExtendIn,
    AdminGrantIn,
    AdminLimitsIn,
    AdminPlanIn,
    AdminPlanPatchIn,
    AdminPromoIn,
    AdminProxyGrantIn,
    AdminWebLoginIn,
    PlanOut,
    StatsOut,
)
from app.services.marzban import MarzbanClient, to_unix
from app.services.provisioning import (
    get_active_subscription,
    grant_subscription,
    mark_order_paid,
    revoke_subscription,
    serialize_subscription,
    update_subscription_limits,
)
from app.services.proxy import (
    count_active_proxy_users,
    get_proxy_access,
    grant_or_extend_proxy,
    proxy_configured,
    revoke_proxy_access,
    serialize_proxy_access,
)
from app.services.telegram_notify import send_telegram_message

router = APIRouter(prefix="/admin", tags=["admin"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/web/login")
async def web_admin_login(
    body: AdminWebLoginIn,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Browser admin login for the :1110 panel. No bot token required."""
    username = (settings.admin_web_username or "").strip()
    password = settings.admin_web_password or ""
    if not username or not password:
        raise HTTPException(status_code=503, detail="Web admin is not configured")
    user_ok = secrets.compare_digest(body.username.strip(), username)
    pass_ok = secrets.compare_digest(body.password, password)
    if not (user_ok and pass_ok):
        raise HTTPException(status_code=401, detail="Invalid login or password")
    expire = _now() + timedelta(minutes=settings.admin_web_jwt_expire_minutes)
    token = jwt.encode(
        {"sub": username, "role": "web_admin", "exp": expire},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expire.isoformat(),
        "username": username,
    }


@router.get("/web/me")
async def web_admin_me(
    auth: dict = Depends(require_admin_api),
) -> dict:
    return {"ok": True, "auth": auth}


def _bytes_to_gb(value: int | float | None) -> float:
    if not value:
        return 0.0
    return round(float(value) / (1024**3), 3)


async def _vpn_status(sub: Subscription | None, settings: Settings) -> dict | None:
    if not sub or not sub.marzban_username:
        return None
    try:
        data = await MarzbanClient(settings).get_user(sub.marzban_username)
    except Exception as exc:
        return {"error": str(exc), "username": sub.marzban_username}
    if not data:
        return {"username": sub.marzban_username, "found": False}
    used = data.get("used_traffic") or 0
    # Best-effort sync used traffic into DB field for display consistency
    try:
        sub.traffic_used_gb = Decimal(str(_bytes_to_gb(used)))
    except Exception:
        pass
    return {
        "username": sub.marzban_username,
        "found": True,
        "status": data.get("status"),
        "online_at": data.get("online_at"),
        "used_traffic_bytes": used,
        "used_traffic_gb": _bytes_to_gb(used),
        "data_limit_bytes": data.get("data_limit") or 0,
        "expire": data.get("expire"),
    }


async def _user_payload(db: AsyncSession, user: User, settings: Settings) -> dict:
    sub = await get_active_subscription(db, user.id)
    if not sub:
        # Include disabled/expired so admin can still open revoked users.
        result = await db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.ends_at.desc())
            .limit(1)
        )
        sub = result.scalar_one_or_none()
    vpn = await _vpn_status(sub, settings)
    if sub and vpn and vpn.get("used_traffic_gb") is not None:
        try:
            await db.commit()
        except Exception:
            await db.rollback()
    proxy = serialize_proxy_access(await get_proxy_access(db, user.id), settings)
    return {
        "user": {
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "subscription": serialize_subscription(sub, settings) if sub else None,
            "proxy": proxy,
            "vpn": vpn,
        }
    }


@router.get("/stats", response_model=StatsOut)
async def stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> StatsOut:
    users_total = await db.scalar(select(func.count()).select_from(User)) or 0
    active = await db.scalar(
        select(func.count()).select_from(Subscription).where(Subscription.status == SubscriptionStatus.active)
    ) or 0
    trial = await db.scalar(
        select(func.count()).select_from(Subscription).where(Subscription.status == SubscriptionStatus.trial)
    ) or 0
    paid_orders = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.paid)
    ) or 0
    pending_orders = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.pending)
    ) or 0

    result = await db.execute(
        select(Plan.price_rub, Plan.duration_days)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.status == SubscriptionStatus.active)
    )
    mrr = Decimal("0")
    for price, days in result.all():
        if days and days > 0:
            mrr += Decimal(price) * Decimal(30) / Decimal(days)

    start_today = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_7d = _now() - timedelta(days=7)
    revenue_today = await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status == OrderStatus.paid,
            Order.paid_at >= start_today,
        )
    ) or Decimal("0")
    revenue_7d = await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status == OrderStatus.paid,
            Order.paid_at >= start_7d,
        )
    ) or Decimal("0")

    return StatsOut(
        users_total=users_total,
        subscriptions_active=active,
        subscriptions_trial=trial,
        orders_paid=paid_orders,
        mrr_rub=mrr.quantize(Decimal("0.01")),
        revenue_today_rub=Decimal(revenue_today).quantize(Decimal("0.01")),
        revenue_7d_rub=Decimal(revenue_7d).quantize(Decimal("0.01")),
        pending_orders=int(pending_orders),
    )


@router.get("/health")
async def admin_health(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> dict:
    db_ok = False
    try:
        await db.execute(select(1))
        db_ok = True
    except Exception:
        db_ok = False

    marzban = MarzbanClient(settings)
    marzban_ok = await marzban.health()
    marzban_system = await marzban.system_info() if marzban_ok else None

    mem = {"total_mb": None, "available_mb": None}
    try:
        with open("/proc/meminfo") as f:
            info = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])
            mem = {
                "total_mb": round(info.get("MemTotal", 0) / 1024, 1),
                "available_mb": round(info.get("MemAvailable", 0) / 1024, 1),
            }
    except Exception:
        pass

    disk = {}
    try:
        usage = shutil.disk_usage("/")
        disk = {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
        }
    except Exception:
        pass

    port = int(os.getenv("REALITY_PORT", "52250"))
    host = os.getenv("REALITY_CHECK_HOST", "host.docker.internal")
    reality_open = False
    try:
        await asyncio.to_thread(socket.create_connection, (host, port), 3)
        reality_open = True
    except Exception:
        reality_open = False

    return {
        "ok": db_ok and marzban_ok,
        "db": db_ok,
        "marzban": marzban_ok,
        "marzban_system": marzban_system,
        "memory": mem,
        "disk": disk,
        "reality": {"host": host, "port": port, "open": reality_open},
        "loadavg": os.getloadavg() if hasattr(os, "getloadavg") else None,
    }


@router.get("/users")
async def list_users(
    status_filter: str | None = Query(default="active", alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """List recent users. status=active|trial|all|recent"""
    if status_filter in {"active", "trial"}:
        st = SubscriptionStatus.active if status_filter == "active" else SubscriptionStatus.trial
        q = (
            select(User, Subscription)
            .join(Subscription, Subscription.user_id == User.id)
            .where(Subscription.status == st, Subscription.ends_at > _now())
            .order_by(Subscription.ends_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(q)).all()
        items = []
        for user, sub in rows:
            items.append(
                {
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "status": sub.status.value,
                    "ends_at": sub.ends_at.isoformat(),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
            )
        return {"items": items, "filter": status_filter}

    q = select(User).order_by(User.created_at.desc()).limit(limit)
    users = (await db.execute(q)).scalars().all()
    items = []
    for user in users:
        sub = await get_active_subscription(db, user.id)
        items.append(
            {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "status": sub.status.value if sub else None,
                "ends_at": sub.ends_at.isoformat() if sub else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        )
    return {"items": items, "filter": status_filter or "recent"}


@router.get("/users/lookup")
async def lookup_user(
    q: str = Query(min_length=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    raw = q.strip().lstrip("@")
    user = None
    if raw.isdigit():
        result = await db.execute(select(User).where(User.telegram_id == int(raw)))
        user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(func.lower(User.username) == raw.lower()))
        user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await _user_payload(db, user, settings)


@router.get("/users/{telegram_id}")
async def user_by_telegram(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await _user_payload(db, user, settings)


@router.post("/users/{telegram_id}/extend")
async def extend_user(
    telegram_id: int,
    body: AdminExtendIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Silent extend — no Telegram notify to the user."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    sub = await get_active_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    now = _now()
    base = sub.ends_at if sub.ends_at > now else now
    sub.ends_at = base + timedelta(days=body.days)
    sub.status = SubscriptionStatus.active
    if sub.marzban_username:
        await MarzbanClient(settings).modify_user(
            sub.marzban_username, expire_ts=to_unix(sub.ends_at), status="active"
        )
    await db.commit()
    await db.refresh(sub)
    return {"ok": True, "ends_at": sub.ends_at.isoformat(), "notified": False}


@router.post("/users/{telegram_id}/grant")
async def grant_user(
    telegram_id: int,
    body: AdminGrantIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Silent grant — no Telegram notify to the user."""
    user = await get_or_create_telegram_user(
        db, telegram_id, username=body.username, settings=settings
    )
    await db.commit()
    sub = await grant_subscription(
        db,
        user=user,
        days=body.days,
        traffic_gb=body.traffic_gb,
        clear_traffic_limit=body.clear_traffic_limit or body.traffic_gb == 0,
        device_limit=body.device_limit,
        settings=settings,
        notify=False,
    )
    return {
        "ok": True,
        "subscription": serialize_subscription(sub, settings),
        "ends_at": sub.ends_at.isoformat(),
        "notified": False,
    }


@router.post("/users/{telegram_id}/revoke")
async def revoke_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Disable subscription + Marzban cut-off. Silent."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    sub = await revoke_subscription(db, user=user, settings=settings)
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription")
    return {
        "ok": True,
        "status": sub.status.value,
        "telegram_id": telegram_id,
        "notified": False,
    }


@router.get("/proxy/info")
async def proxy_info(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    from app.services.proxy import mtproto_configured, proxy_mode, socks_configured

    configured = proxy_configured(settings)
    mode = proxy_mode(settings)
    payload: dict = {
        "configured": configured,
        "enabled": configured,
        "type": mode,
        "active_users": await count_active_proxy_users(db),
    }
    if mode == "socks5" and socks_configured(settings):
        payload.update({"host": settings.socks5_host, "port": str(settings.socks5_port)})
    elif mode == "mtproto" and mtproto_configured(settings):
        payload.update(
            {
                "host": settings.mtproto_host,
                "port": str(settings.mtproto_port),
                "secret_preview": f"{settings.mtproto_secret[:10]}…",
            }
        )
    return payload


@router.post("/users/{telegram_id}/proxy/grant")
async def grant_proxy_user(
    telegram_id: int,
    body: AdminProxyGrantIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Silent SOCKS5 proxy grant/extend — no Telegram notify."""
    if not proxy_configured(settings):
        raise HTTPException(status_code=503, detail="Proxy is not configured on server")
    user = await get_or_create_telegram_user(
        db, telegram_id, username=body.username, settings=settings
    )
    await db.commit()
    access = await grant_or_extend_proxy(
        db, user=user, days=body.days, stack=body.stack
    )
    await db.commit()
    await db.refresh(access)
    return {
        "ok": True,
        "proxy": serialize_proxy_access(access, settings),
        "ends_at": access.ends_at.isoformat(),
        "notified": False,
    }


@router.post("/users/{telegram_id}/proxy/revoke")
async def revoke_proxy_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Silent SOCKS5 proxy revoke (removes login from 3proxy)."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    access = await revoke_proxy_access(db, user=user)
    if not access:
        raise HTTPException(status_code=404, detail="No proxy access")
    await db.commit()
    return {
        "ok": True,
        "proxy": serialize_proxy_access(access, settings, include_credentials=False),
        "status": access.status.value,
        "notified": False,
    }


@router.post("/users/{telegram_id}/limits")
async def patch_limits(
    telegram_id: int,
    body: AdminLimitsIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Update traffic/device limits without re-issuing days. Silent."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        sub = await update_subscription_limits(
            db,
            user=user,
            traffic_gb=body.traffic_gb,
            clear_traffic_limit=body.clear_traffic_limit,
            device_limit=body.device_limit,
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "ok": True,
        "subscription": serialize_subscription(sub, settings),
        "notified": False,
    }


@router.get("/orders")
async def list_orders(
    status: str = Query(default="pending"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> dict:
    try:
        st = OrderStatus(status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid status") from exc
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.plan))
        .where(Order.status == st)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    items = []
    for order in result.scalars().all():
        items.append(
            {
                "payment_label": order.payment_label,
                "amount": str(order.amount),
                "currency": order.currency,
                "status": order.status.value,
                "telegram_id": order.user.telegram_id if order.user else None,
                "username": order.user.username if order.user else None,
                "plan": order.plan.name if order.plan else None,
                "created_at": order.created_at.isoformat() if order.created_at else None,
            }
        )
    return {"items": items, "status": status}


@router.post("/orders/{payment_label}/confirm")
async def confirm_order_by_label(
    payment_label: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Manual payment confirmation. Silent — user is not notified."""
    result = await db.execute(select(Order).where(Order.payment_label == payment_label))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order, sub, created = await mark_order_paid(
        db,
        order=order,
        external_id=order.payment_external_id or f"manual-{payment_label}",
        raw={"manual": True, "label": payment_label},
        settings=settings,
    )
    return {
        "ok": True,
        "created": created,
        "order_status": order.status.value,
        "subscription": serialize_subscription(sub, settings) if sub else None,
        "notified": False,
    }


@router.post("/broadcast")
async def broadcast(
    body: AdminBroadcastIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Explicit admin broadcast. Only fires when admin confirms in the bot."""
    audience = (body.audience or "active").lower()
    if audience not in {"all", "active"}:
        raise HTTPException(status_code=400, detail="audience must be all|active")

    if audience == "all":
        result = await db.execute(
            select(User.telegram_id).where(User.telegram_id.is_not(None))
        )
        chat_ids = [int(x) for x in result.scalars().all() if x]
    else:
        result = await db.execute(
            select(User.telegram_id)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                User.telegram_id.is_not(None),
                Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trial]),
                Subscription.ends_at > _now(),
            )
            .distinct()
        )
        chat_ids = [int(x) for x in result.scalars().all() if x]

    # Never broadcast to empty / self-only accidentally without targets
    sent = 0
    failed = 0
    for chat_id in chat_ids:
        ok = await send_telegram_message(chat_id, body.text, settings=settings)
        if ok:
            sent += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)
    return {"ok": True, "audience": audience, "targets": len(chat_ids), "sent": sent, "failed": failed}


@router.get("/plans", response_model=list[PlanOut])
async def admin_plans(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> list[Plan]:
    result = await db.execute(select(Plan).order_by(Plan.sort_order))
    return list(result.scalars().all())


@router.post("/plans", response_model=PlanOut)
async def create_plan(
    body: AdminPlanIn,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> Plan:
    existing = await db.scalar(select(Plan).where(Plan.slug == body.slug))
    if existing:
        raise HTTPException(status_code=409, detail="slug already exists")
    plan = Plan(
        slug=body.slug,
        name=body.name,
        group_name=body.group_name,
        duration_days=body.duration_days,
        traffic_gb=body.traffic_gb,
        device_limit=body.device_limit,
        price_rub=body.price_rub,
        is_active=body.is_active,
        sort_order=body.sort_order,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanOut)
async def patch_plan(
    plan_id: UUID,
    body: AdminPlanPatchIn,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> Plan:
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/promos")
async def list_promos(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> dict:
    result = await db.execute(select(PromoCode).order_by(PromoCode.created_at.desc()).limit(50))
    items = []
    for p in result.scalars().all():
        items.append(
            {
                "id": str(p.id),
                "code": p.code,
                "days": p.days,
                "traffic_gb": p.traffic_gb,
                "device_limit": p.device_limit,
                "max_uses": p.max_uses,
                "used_count": p.used_count,
                "is_active": p.is_active,
                "note": p.note,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
        )
    return {"items": items}


@router.post("/promos")
async def create_promo(
    body: AdminPromoIn,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> dict:
    code = body.code.strip().upper()
    existing = await db.scalar(select(PromoCode).where(func.upper(PromoCode.code) == code))
    if existing:
        raise HTTPException(status_code=409, detail="code exists")
    promo = PromoCode(
        code=code,
        days=body.days,
        traffic_gb=body.traffic_gb,
        device_limit=body.device_limit,
        max_uses=body.max_uses,
        note=body.note,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return {"ok": True, "code": promo.code, "id": str(promo.id)}


@router.post("/promos/{code}/disable")
async def disable_promo(
    code: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> dict:
    promo = await db.scalar(select(PromoCode).where(func.upper(PromoCode.code) == code.strip().upper()))
    if not promo:
        raise HTTPException(status_code=404, detail="Promo not found")
    promo.is_active = False
    await db.commit()
    return {"ok": True, "code": promo.code, "is_active": False}


@router.post("/promos/{code}/redeem")
async def redeem_promo_admin(
    code: str,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api),
) -> dict:
    """Admin-driven silent promo redeem for a specific user."""
    from app.models.entities import PromoRedemption

    promo = await db.scalar(select(PromoCode).where(func.upper(PromoCode.code) == code.strip().upper()))
    if not promo or not promo.is_active:
        raise HTTPException(status_code=404, detail="Promo inactive or missing")
    if promo.expires_at and promo.expires_at <= _now():
        raise HTTPException(status_code=400, detail="Promo expired")
    if promo.max_uses is not None and promo.used_count >= promo.max_uses:
        raise HTTPException(status_code=400, detail="Promo exhausted")
    user = await get_or_create_telegram_user(db, telegram_id, settings=settings)
    await db.commit()
    existing = await db.scalar(
        select(PromoRedemption).where(PromoRedemption.promo_id == promo.id, PromoRedemption.user_id == user.id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already redeemed by this user")
    sub = await grant_subscription(
        db,
        user=user,
        days=promo.days,
        traffic_gb=promo.traffic_gb,
        clear_traffic_limit=promo.traffic_gb is None,
        device_limit=promo.device_limit,
        settings=settings,
        notify=False,
    )
    db.add(PromoRedemption(promo_id=promo.id, user_id=user.id))
    promo.used_count += 1
    await db.commit()
    return {
        "ok": True,
        "code": promo.code,
        "telegram_id": telegram_id,
        "ends_at": sub.ends_at.isoformat(),
        "notified": False,
    }


@router.get("/export.csv")
async def export_csv(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> StreamingResponse:
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(5000))
    users = list(result.scalars().all())
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["telegram_id", "username", "is_admin", "created_at", "sub_status", "ends_at", "traffic_limit_gb", "device_limit"]
    )
    for user in users:
        sub = await get_active_subscription(db, user.id)
        writer.writerow(
            [
                user.telegram_id or "",
                user.username or "",
                int(user.is_admin),
                user.created_at.isoformat() if user.created_at else "",
                sub.status.value if sub else "",
                sub.ends_at.isoformat() if sub else "",
                sub.traffic_limit_gb if sub and sub.traffic_limit_gb is not None else "",
                sub.device_limit if sub else "",
            ]
        )
    data = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enigma_users.csv"},
    )


@router.get("/subscriptions")
async def admin_subscriptions(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin_api),
) -> list[dict]:
    result = await db.execute(
        select(Subscription).options(selectinload(Subscription.user), selectinload(Subscription.plan)).limit(100)
    )
    rows = []
    for sub in result.scalars().all():
        rows.append(
            {
                "id": str(sub.id),
                "status": sub.status.value,
                "telegram_id": sub.user.telegram_id if sub.user else None,
                "ends_at": sub.ends_at.isoformat(),
                "plan": sub.plan.name if sub.plan else "trial",
            }
        )
    return rows
