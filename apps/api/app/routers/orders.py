from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_or_create_telegram_user, require_bot
from app.models.entities import Order, Plan
from app.schemas import OrderCreateIn, OrderOut
from app.services.provisioning import create_order
from app.services.yoomoney import YooMoneyProvider

router = APIRouter(prefix="/api/v1", tags=["orders"])


@router.post("/orders", response_model=OrderOut)
async def create_order_endpoint(
    body: OrderCreateIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_bot),
) -> OrderOut:
    if not body.telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id required")
    plan = await db.get(Plan, body.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found")
    user = await get_or_create_telegram_user(db, body.telegram_id, settings=settings)
    await db.commit()
    order = await create_order(db, user, plan)
    provider = YooMoneyProvider(settings)
    redirect = provider.create_payment(order, description=f"{settings.brand_name}: {plan.name}")
    return OrderOut(
        id=order.id,
        status=order.status.value,
        amount=order.amount,
        currency=order.currency,
        payment_provider=order.payment_provider,
        payment_label=order.payment_label,
        payment_url=redirect.payment_url,
        created_at=order.created_at,
        paid_at=order.paid_at,
    )


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_bot),
) -> OrderOut:
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    provider = YooMoneyProvider(settings)
    plan = await db.get(Plan, order.plan_id)
    redirect = provider.create_payment(order, description=f"{settings.brand_name}: {plan.name if plan else 'VPN'}")
    return OrderOut(
        id=order.id,
        status=order.status.value,
        amount=order.amount,
        currency=order.currency,
        payment_provider=order.payment_provider,
        payment_label=order.payment_label,
        payment_url=redirect.payment_url,
        created_at=order.created_at,
        paid_at=order.paid_at,
    )
