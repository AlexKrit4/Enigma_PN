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
from app.services.happ import build_happ_deep_link, build_sub_url
from app.services.marzban import MarzbanClient, to_unix

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


def serialize_subscription(sub: Subscription | None, settings: Settings | None = None) -> dict | None:
    if not sub:
        return None
    settings = settings or get_settings()
    sub_url = build_sub_url(sub.sub_token, settings)
    return {
        "id": sub.id,
        "status": sub.status.value,
        "starts_at": sub.starts_at,
        "ends_at": sub.ends_at,
        "traffic_limit_gb": sub.traffic_limit_gb,
        "traffic_used_gb": sub.traffic_used_gb,
        "device_limit": sub.device_limit,
        "sub_url": sub_url,
        "happ_deep_link": build_happ_deep_link(sub_url),
        "plan": sub.plan,
    }


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

    client = await marzban.create_user(
        username=username,
        expire_ts=to_unix(subscription.ends_at),
        data_limit_bytes=data_limit,
        note=f"enigma:{subscription.id}",
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
    plan = await db.get(Plan, order.plan_id)
    if not plan:
        raise ValueError("Plan not found")

    active = await get_active_subscription(db, order.user_id)
    if active and active.marzban_username:
        # Extend existing
        base = active.ends_at if active.ends_at > _now() else _now()
        active.ends_at = base + timedelta(days=plan.duration_days)
        active.status = SubscriptionStatus.active
        active.plan_id = plan.id
        active.order_id = order.id
        active.traffic_limit_gb = plan.traffic_gb
        active.device_limit = plan.device_limit
        active.reminder_sent = False
        marzban = MarzbanClient(settings)
        data_limit = int(plan.traffic_gb * 1024**3) if plan.traffic_gb else 0
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
        plan_id=plan.id,
        order_id=order.id,
        status=SubscriptionStatus.active,
        starts_at=_now(),
        ends_at=_now() + timedelta(days=plan.duration_days),
        traffic_limit_gb=plan.traffic_gb,
        device_limit=plan.device_limit,
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


async def create_order(db: AsyncSession, user: User, plan: Plan) -> Order:
    order = Order(
        user_id=user.id,
        plan_id=plan.id,
        amount=Decimal(plan.price_rub),
        currency="RUB",
        status=OrderStatus.pending,
        payment_provider="yoomoney",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order
