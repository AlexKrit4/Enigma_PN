from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_or_create_telegram_user, require_bot
from app.models.entities import Order, Plan
from app.schemas import CustomOrderCreateIn, CustomQuoteIn, OrderCreateIn, OrderOut
from app.services.pricing import calc_custom_price, custom_price_breakdown, validate_custom_tariff
from app.services.provisioning import create_order
from app.services.yoomoney import YooMoneyProvider

router = APIRouter(prefix="/api/v1", tags=["orders"])


def _order_out(order: Order, payment_url: str | None = None) -> OrderOut:
    meta = order.meta or {}
    return OrderOut(
        id=order.id,
        status=order.status.value,
        amount=order.amount,
        currency=order.currency,
        payment_provider=order.payment_provider,
        payment_label=order.payment_label,
        payment_url=payment_url,
        created_at=order.created_at,
        paid_at=order.paid_at,
        title=meta.get("title"),
        meta=meta,
    )


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
    return _order_out(order, redirect.payment_url)


@router.post("/orders/custom/quote")
async def quote_custom_order(
    body: CustomQuoteIn,
    _: None = Depends(require_bot),
) -> dict:
    try:
        return custom_price_breakdown(
            traffic_gb=body.traffic_gb,
            days=body.days,
            device_limit=body.device_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/custom", response_model=OrderOut)
async def create_custom_order_endpoint(
    body: CustomOrderCreateIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_bot),
) -> OrderOut:
    try:
        validate_custom_tariff(
            traffic_gb=body.traffic_gb,
            days=body.days,
            device_limit=body.device_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    breakdown = custom_price_breakdown(
        traffic_gb=body.traffic_gb,
        days=body.days,
        device_limit=body.device_limit,
    )
    amount = calc_custom_price(
        traffic_gb=body.traffic_gb,
        days=body.days,
        device_limit=body.device_limit,
    )
    if amount < Decimal("1.00"):
        raise HTTPException(status_code=400, detail="Amount too small")

    user = await get_or_create_telegram_user(db, body.telegram_id, settings=settings)
    await db.commit()
    order = await create_order(
        db,
        user,
        plan=None,
        amount=amount,
        duration_days=body.days,
        traffic_gb=body.traffic_gb,
        device_limit=body.device_limit,
        title=breakdown["title"],
        kind="свой",
        meta_extra={
            "gb_cost": breakdown["gb_cost"],
            "days_cost": breakdown["days_cost"],
            "devices_cost": breakdown["devices_cost"],
        },
    )
    provider = YooMoneyProvider(settings)
    redirect = provider.create_payment(
        order,
        description=f"{settings.brand_name}: {breakdown['title']}",
    )
    return _order_out(order, redirect.payment_url)


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
    title = (order.meta or {}).get("title")
    if not title and order.plan_id:
        plan = await db.get(Plan, order.plan_id)
        title = plan.name if plan else "VPN"
    redirect = provider.create_payment(order, description=f"{settings.brand_name}: {title or 'VPN'}")
    return _order_out(order, redirect.payment_url)
