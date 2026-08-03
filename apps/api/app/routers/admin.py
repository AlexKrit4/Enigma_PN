from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import require_bot
from app.models.entities import Order, OrderStatus, Plan, Subscription, SubscriptionStatus, User
from app.schemas import AdminExtendIn, PlanOut, StatsOut, UserOut
from app.services.marzban import MarzbanClient, to_unix
from app.services.provisioning import get_active_subscription, serialize_subscription

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=StatsOut)
async def stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_bot),
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

    # Approximate MRR from active paid plans
    result = await db.execute(
        select(Plan.price_rub, Plan.duration_days)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.status == SubscriptionStatus.active)
    )
    mrr = Decimal("0")
    for price, days in result.all():
        if days and days > 0:
            mrr += Decimal(price) * Decimal(30) / Decimal(days)

    return StatsOut(
        users_total=users_total,
        subscriptions_active=active,
        subscriptions_trial=trial,
        orders_paid=paid_orders,
        mrr_rub=mrr.quantize(Decimal("0.01")),
    )


@router.get("/users/{telegram_id}")
async def user_by_telegram(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_bot),
) -> dict:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    sub = await get_active_subscription(db, user.id)
    return {
        "user": UserOut(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
            subscription=serialize_subscription(sub, settings),  # type: ignore[arg-type]
        )
    }


@router.post("/users/{telegram_id}/extend")
async def extend_user(
    telegram_id: int,
    body: AdminExtendIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_bot),
) -> dict:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    sub = await get_active_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    now = datetime.now(timezone.utc)
    base = sub.ends_at if sub.ends_at > now else now
    sub.ends_at = base + timedelta(days=body.days)
    sub.status = SubscriptionStatus.active
    if sub.marzban_username:
        await MarzbanClient(settings).modify_user(sub.marzban_username, expire_ts=to_unix(sub.ends_at), status="active")
    await db.commit()
    return {"ok": True, "ends_at": sub.ends_at.isoformat()}


@router.get("/plans", response_model=list[PlanOut])
async def admin_plans(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_bot),
) -> list[Plan]:
    result = await db.execute(select(Plan).order_by(Plan.sort_order))
    return list(result.scalars().all())


@router.get("/subscriptions")
async def admin_subscriptions(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_bot),
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
