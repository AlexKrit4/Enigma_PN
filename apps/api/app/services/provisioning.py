from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.models.entities import (
    Order,
    OrderStatus,
    Payment,
    Plan,
    Subscription,
    SubscriptionStatus,
    User,
    VpnNode,
)
from app.services.happ import build_happ_deep_link, build_happ_open_url, build_sub_url
from app.services.marzban import MarzbanClient, to_unix
from app.services.telegram_notify import send_telegram_message

log = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def pick_node(db: AsyncSession, settings: Settings) -> VpnNode | None:
    result = await db.execute(
        select(VpnNode).where(VpnNode.is_enabled.is_(True)).order_by(VpnNode.current_users.asc(), VpnNode.weight.desc())
    )
    node = result.scalars().first()
    if node:
        return node
    # Fallback to env nodes without DB row
    if settings.vpn_nodes:
        cfg = settings.vpn_nodes[0]
        node = VpnNode(id=str(cfg["id"]), name=str(cfg["name"]), weight=int(cfg.get("weight", 100)))
        db.add(node)
        await db.flush()
        return node
    return None


async def get_active_subscription(db: AsyncSession, user_id: UUID) -> Subscription | None:
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubscriptionStatus.trial, SubscriptionStatus.active]),
            Subscription.ends_at > _now(),
        )
        .order_by(Subscription.ends_at.desc())
    )
    return result.scalars().first()


def serialize_subscription(
    sub: Subscription | None,
    settings: Settings | None = None,
    *,
    devices_used: int | None = None,
    devices: list[dict] | None = None,
    title: str | None = None,
) -> dict | None:
    if not sub:
        return None
    settings = settings or get_settings()
    sub_url = build_sub_url(sub.sub_token, settings)
    plan_data = None
    # Avoid async lazy-load of relationship outside greenlet context.
    try:
        from sqlalchemy import inspect as sa_inspect

        state = sa_inspect(sub)
        plan_loaded = "plan" not in state.unloaded
    except Exception:
        plan_loaded = False
    if plan_loaded:
        plan = sub.plan
        if plan is not None:
            plan_data = {
                "id": str(plan.id),
                "slug": plan.slug,
                "name": plan.name,
                "group_name": plan.group_name,
                "duration_days": plan.duration_days,
                "traffic_gb": plan.traffic_gb,
                "device_limit": plan.device_limit,
                "price_rub": str(plan.price_rub),
                "is_active": plan.is_active,
                "sort_order": plan.sort_order,
            }
    display_title = title
    if not display_title and plan_data:
        display_title = plan_data.get("name")
    # If order title exists and a stale plan is still linked, prefer order title in plan card.
    if title and plan_data is not None:
        plan_data = {**plan_data, "name": title}
    data = {
        "id": str(sub.id),
        "status": sub.status.value,
        "starts_at": sub.starts_at.isoformat() if sub.starts_at else None,
        "ends_at": sub.ends_at.isoformat() if sub.ends_at else None,
        "traffic_limit_gb": sub.traffic_limit_gb,
        "traffic_used_gb": str(sub.traffic_used_gb),
        "device_limit": sub.device_limit,
        "devices_used": devices_used if devices_used is not None else 0,
        "title": display_title,
        "sub_url": sub_url,
        "happ_deep_link": build_happ_deep_link(sub_url),
        "happ_open_url": build_happ_open_url(sub.sub_token, settings),
        "plan": plan_data,
    }
    if devices is not None:
        data["devices"] = devices
    return data


async def serialize_subscription_with_devices(
    db: AsyncSession,
    sub: Subscription | None,
    settings: Settings | None = None,
    *,
    include_devices: bool = False,
) -> dict | None:
    if not sub:
        return None
    from app.services.devices import active_device_count, list_devices, serialize_device

    used = await active_device_count(db, sub.id)
    devices_payload = None
    if include_devices:
        devices_payload = [serialize_device(d) for d in await list_devices(db, sub.id) if not d.is_blocked]

    title = None
    if sub.order_id:
        order = await db.get(Order, sub.order_id)
        if order and order.meta:
            title = order.meta.get("title")

    return serialize_subscription(
        sub,
        settings,
        devices_used=used,
        devices=devices_payload,
        title=title,
    )


async def create_trial(db: AsyncSession, user: User, settings: Settings | None = None) -> Subscription | None:
    settings = settings or get_settings()
    if not settings.trial_enabled:
        return None
    existing = await get_active_subscription(db, user.id)
    if existing:
        return existing

    # Only one trial ever
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.trial,
        )
    )
    if result.scalars().first():
        return None

    ends = _now() + timedelta(days=settings.trial_duration_days)
    sub = Subscription(
        user_id=user.id,
        status=SubscriptionStatus.trial,
        starts_at=_now(),
        ends_at=ends,
        traffic_limit_gb=settings.trial_traffic_gb,
        device_limit=settings.trial_device_limit,
    )
    db.add(sub)
    await db.flush()
    await provision_subscription(db, sub, settings=settings)
    await db.commit()
    await db.refresh(sub)
    return sub


async def provision_subscription(
    db: AsyncSession,
    subscription: Subscription,
    settings: Settings | None = None,
) -> Subscription:
    settings = settings or get_settings()
    marzban = MarzbanClient(settings)
    node = await pick_node(db, settings)
    username = subscription.marzban_username or f"u{str(subscription.user_id).replace('-', '')[:16]}"
    data_limit = None
    if subscription.traffic_limit_gb is not None:
        data_limit = int(subscription.traffic_limit_gb * 1024**3)

    try:
        client = await marzban.create_user(
            username=username,
            expire_ts=to_unix(subscription.ends_at),
            data_limit_bytes=data_limit,
            note=f"enigma:{subscription.id}",
        )
    except Exception as exc:
        # Username already exists in Marzban — reactivate/update instead.
        if "409" not in str(exc) and "Conflict" not in str(exc):
            raise
        log.warning("marzban_create_conflict_reuse", username=username, error=str(exc))
        await marzban.modify_user(
            username,
            expire_ts=to_unix(subscription.ends_at),
            status="active",
            data_limit_bytes=data_limit or 0,
        )
        existing = await marzban.get_user(username) or {}
        import uuid as uuid_mod

        user_uuid = uuid_mod.UUID(
            existing.get("proxies", {}).get("vless", {}).get("id") or str(uuid_mod.uuid4())
        )
        from app.services.marzban import ProvisionedClient

        client = ProvisionedClient(
            username=username,
            uuid=user_uuid,
            node_id=settings.vpn_nodes[0]["id"] if settings.vpn_nodes else "nl-1",
            links=list(existing.get("links") or []),
            raw=existing,
        )

    subscription.marzban_username = client.username
    subscription.marzban_uuid = client.uuid
    subscription.node_id = client.node_id
    if node:
        node.current_users = (node.current_users or 0) + 1
    await db.flush()
    log.info("provisioned", subscription_id=str(subscription.id), username=username, mock=settings.marzban_mock)
    return subscription


async def activate_paid_order(db: AsyncSession, order: Order, settings: Settings | None = None) -> Subscription:
    settings = settings or get_settings()
    from app.services.pricing import order_terms

    plan = await db.get(Plan, order.plan_id) if order.plan_id else None
    terms = order_terms(order.meta, plan)
    duration_days = int(terms["duration_days"])
    traffic_gb = terms.get("traffic_gb")
    device_limit = int(terms["device_limit"])
    meta = order.meta or {}
    # Custom packages are exact: N days from purchase moment, not stacked on old plan leftovers.
    is_custom = (meta.get("kind") == "свой") or (plan is None)

    active = await get_active_subscription(db, order.user_id)
    if not active:
        # Reuse disabled/expired row to avoid Marzban username 409.
        result = await db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.user_id == order.user_id)
            .order_by(Subscription.ends_at.desc())
            .limit(1)
        )
        active = result.scalar_one_or_none()

    if active and active.marzban_username:
        now = _now()
        if is_custom:
            active.ends_at = now + timedelta(days=duration_days)
            active.starts_at = now
        else:
            base = active.ends_at if active.ends_at > now else now
            active.ends_at = base + timedelta(days=duration_days)
        active.status = SubscriptionStatus.active
        # Never keep a stale catalog plan on a custom purchase.
        active.plan_id = plan.id if plan else None
        active.order_id = order.id
        active.traffic_limit_gb = traffic_gb
        active.device_limit = device_limit
        active.reminder_sent = False
        marzban = MarzbanClient(settings)
        data_limit = int(traffic_gb * 1024**3) if traffic_gb else 0
        await marzban.modify_user(
            active.marzban_username,
            expire_ts=to_unix(active.ends_at),
            status="active",
            data_limit_bytes=data_limit,
        )
        await db.flush()
        return active

    sub = Subscription(
        user_id=order.user_id,
        plan_id=plan.id if plan else None,
        order_id=order.id,
        status=SubscriptionStatus.active,
        starts_at=_now(),
        ends_at=_now() + timedelta(days=duration_days),
        traffic_limit_gb=traffic_gb,
        device_limit=device_limit,
    )
    db.add(sub)
    await db.flush()
    await provision_subscription(db, sub, settings=settings)
    return sub


async def mark_order_paid(
    db: AsyncSession,
    *,
    order: Order,
    external_id: str,
    raw: dict,
    settings: Settings | None = None,
) -> tuple[Order, Subscription | None, bool]:
    """Idempotent payment confirmation. Returns (order, subscription, created_new)."""
    settings = settings or get_settings()

    # Already processed by external id
    existing_payment = await db.execute(
        select(Payment).where(Payment.provider == "yoomoney", Payment.external_id == external_id)
    )
    if existing_payment.scalars().first():
        sub = await get_active_subscription(db, order.user_id)
        return order, sub, False

    if order.status == OrderStatus.paid:
        sub = await get_active_subscription(db, order.user_id)
        return order, sub, False

    order.status = OrderStatus.paid
    order.paid_at = _now()
    order.payment_external_id = external_id
    db.add(
        Payment(
            order_id=order.id,
            provider="yoomoney",
            external_id=external_id,
            status="succeeded",
            raw_payload=raw,
        )
    )
    sub = await activate_paid_order(db, order, settings=settings)
    await db.commit()
    await db.refresh(order)
    if sub:
        await db.refresh(sub)
    return order, sub, True


async def notify_subscription_ready(
    db: AsyncSession,
    *,
    user: User,
    sub: Subscription,
    title: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if not user.telegram_id:
        return
    data = serialize_subscription(sub, settings) or {}
    plan = data.get("plan") or {}
    plan_name = plan.get("name") or (
        "Пробный период" if sub.status == SubscriptionStatus.trial else "VPN-доступ"
    )
    ends = sub.ends_at
    ends_label = f"{ends.day:02d}.{ends.month:02d}.{ends.year}"
    limit = data.get("traffic_limit_gb")
    traffic = "безлимит" if limit is None else f"{limit} ГБ"
    open_url = data.get("happ_open_url") or data.get("sub_url") or ""
    text = (
        f"✅ <b>{title}</b>\n\n"
        f"Тариф: <b>{plan_name}</b>\n"
        f"Действует до: <b>{ends_label}</b>\n"
        f"Трафик: <b>{traffic}</b>\n"
        f"Устройств: <b>{sub.device_limit}</b>\n\n"
        "Нажмите кнопку ниже — Happ откроется и подписка добавится сама."
    )
    markup = None
    if open_url.startswith("http"):
        markup = {
            "inline_keyboard": [
                [{"text": "🚀 Открыть в Happ", "url": open_url}],
            ]
        }
    await send_telegram_message(int(user.telegram_id), text, settings=settings, reply_markup=markup)


def _resolve_traffic_limit_gb(
    *,
    traffic_gb: int | None,
    clear_traffic_limit: bool,
    current: int | None = None,
) -> int | None:
    """Normalize admin traffic input.

    - clear_traffic_limit / traffic_gb=0 → unlimited (None)
    - traffic_gb > 0 → set that limit
    - otherwise keep current (for updates) or None (for create)
    """
    if clear_traffic_limit or traffic_gb == 0:
        return None
    if traffic_gb is not None:
        return traffic_gb
    return current


async def grant_subscription(
    db: AsyncSession,
    *,
    user: User,
    days: int,
    traffic_gb: int | None = None,
    clear_traffic_limit: bool = False,
    device_limit: int | None = None,
    settings: Settings | None = None,
    notify: bool = False,
) -> Subscription:
    """Admin: issue/extend a free subscription for N days.

    notify=False by default — admin actions must stay silent for end users.
    Reactivates disabled/expired rows that already have a Marzban user.
    """
    settings = settings or get_settings()
    if days < 1:
        raise ValueError("days must be >= 1")

    active = await get_active_subscription(db, user.id)
    if not active:
        # Reuse latest subscription (disabled/expired) to avoid Marzban 409 on recreate.
        result = await db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.ends_at.desc())
            .limit(1)
        )
        active = result.scalar_one_or_none()

    if active and active.marzban_username:
        if active.status in {SubscriptionStatus.disabled, SubscriptionStatus.expired}:
            # Keep remaining paid time if still in the future; otherwise start now.
            base = active.ends_at if active.ends_at > _now() else _now()
        else:
            base = active.ends_at if active.ends_at > _now() else _now()
        active.ends_at = base + timedelta(days=days)
        active.status = SubscriptionStatus.active
        if clear_traffic_limit or traffic_gb is not None:
            active.traffic_limit_gb = _resolve_traffic_limit_gb(
                traffic_gb=traffic_gb,
                clear_traffic_limit=clear_traffic_limit,
                current=active.traffic_limit_gb,
            )
        if device_limit is not None:
            active.device_limit = device_limit
        active.reminder_sent = False
        marzban = MarzbanClient(settings)
        data_limit = int(active.traffic_limit_gb * 1024**3) if active.traffic_limit_gb else 0
        await marzban.modify_user(
            active.marzban_username,
            expire_ts=to_unix(active.ends_at),
            status="active",
            data_limit_bytes=data_limit,
        )
        await db.commit()
        await db.refresh(active)
        if notify:
            await notify_subscription_ready(
                db, user=user, sub=active, title="Админ выдал/продлил подписку", settings=settings
            )
        return active

    sub = Subscription(
        user_id=user.id,
        status=SubscriptionStatus.active,
        starts_at=_now(),
        ends_at=_now() + timedelta(days=days),
        traffic_limit_gb=_resolve_traffic_limit_gb(
            traffic_gb=traffic_gb,
            clear_traffic_limit=clear_traffic_limit,
            current=None,
        ),
        device_limit=device_limit or settings.default_device_limit,
    )
    db.add(sub)
    await db.flush()
    await provision_subscription(db, sub, settings=settings)
    await db.commit()
    await db.refresh(sub)
    if notify:
        await notify_subscription_ready(
            db, user=user, sub=sub, title="Админ выдал подписку", settings=settings
        )
    return sub


async def revoke_subscription(
    db: AsyncSession,
    *,
    user: User,
    settings: Settings | None = None,
) -> Subscription | None:
    """Disable active subscription and cut off Marzban access. Silent."""
    settings = settings or get_settings()
    sub = await get_active_subscription(db, user.id)
    if not sub:
        # Also try latest non-expired disabled/active for idempotency
        result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.ends_at.desc())
            .limit(1)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return None
    sub.status = SubscriptionStatus.disabled
    if sub.marzban_username:
        try:
            await MarzbanClient(settings).modify_user(sub.marzban_username, status="disabled")
        except Exception as exc:
            log.error("revoke_marzban_failed", error=str(exc), username=sub.marzban_username)
    await db.commit()
    await db.refresh(sub)
    return sub


async def update_subscription_limits(
    db: AsyncSession,
    *,
    user: User,
    traffic_gb: int | None = None,
    clear_traffic_limit: bool = False,
    device_limit: int | None = None,
    settings: Settings | None = None,
) -> Subscription:
    """Update traffic/device limits without changing expiry. Silent."""
    settings = settings or get_settings()
    sub = await get_active_subscription(db, user.id)
    if not sub:
        raise ValueError("No active subscription")
    if clear_traffic_limit:
        sub.traffic_limit_gb = None
    elif traffic_gb is not None:
        sub.traffic_limit_gb = traffic_gb
    if device_limit is not None:
        sub.device_limit = device_limit
    if sub.marzban_username:
        data_limit = int(sub.traffic_limit_gb * 1024**3) if sub.traffic_limit_gb else 0
        await MarzbanClient(settings).modify_user(
            sub.marzban_username,
            data_limit_bytes=data_limit,
            status="active",
        )
    await db.commit()
    await db.refresh(sub)
    return sub


async def expire_due_subscriptions(db: AsyncSession, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    marzban = MarzbanClient(settings)
    result = await db.execute(
        select(Subscription).where(
            Subscription.status.in_([SubscriptionStatus.trial, SubscriptionStatus.active]),
            Subscription.ends_at <= _now(),
        )
    )
    count = 0
    for sub in result.scalars().all():
        sub.status = SubscriptionStatus.expired
        if sub.marzban_username:
            try:
                await marzban.modify_user(sub.marzban_username, status="disabled")
            except Exception as exc:
                log.error("expire_disable_failed", error=str(exc), username=sub.marzban_username)
        count += 1
    await db.commit()
    return count


async def create_order(
    db: AsyncSession,
    user: User,
    plan: Plan | None = None,
    *,
    amount: Decimal | None = None,
    duration_days: int | None = None,
    traffic_gb: int | None = None,
    device_limit: int | None = None,
    title: str | None = None,
    kind: str | None = None,
    meta_extra: dict | None = None,
) -> Order:
    from app.services.pricing import plan_meta

    if plan is None and (duration_days is None or device_limit is None or amount is None):
        raise ValueError("plan or custom terms required")

    if plan is not None:
        meta = plan_meta(plan)
        order_amount = Decimal(plan.price_rub) if amount is None else Decimal(amount)
        plan_id = plan.id
    else:
        meta = {
            "duration_days": int(duration_days or 0),
            "traffic_gb": traffic_gb,
            "device_limit": int(device_limit or 1),
            "title": title or "Свой тариф",
            "kind": kind or "свой",
        }
        order_amount = Decimal(amount)  # type: ignore[arg-type]
        plan_id = None
    if meta_extra:
        meta.update(meta_extra)

    order = Order(
        user_id=user.id,
        plan_id=plan_id,
        amount=order_amount,
        currency="RUB",
        status=OrderStatus.pending,
        payment_provider="yoomoney",
        meta=meta,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order
