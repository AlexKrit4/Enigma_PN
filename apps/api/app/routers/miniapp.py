from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import create_access_token, get_current_user, get_or_create_telegram_user
from app.models.entities import Plan, User
from app.schemas import UserOut
from app.services.casino import (
    BET_DAYS,
    BOOK_COUNT,
    MAX_WIN_DAYS,
    books_rtp,
    casino_eligible,
    paytable_public,
    spin_casino,
)
from app.services.pricing import calc_custom_price, custom_price_breakdown, validate_custom_tariff
from app.services.provisioning import (
    create_order,
    create_trial,
    get_active_subscription,
    serialize_subscription_with_devices,
)
from app.services.telegram_webapp import validate_webapp_init_data
from app.services.yoomoney import YooMoneyProvider

router = APIRouter(prefix="/api/v1/miniapp", tags=["miniapp"])


class MiniAppAuthIn(BaseModel):
    init_data: str = Field(min_length=10)


class MiniAppOrderIn(BaseModel):
    plan_id: UUID


class MiniAppCustomOrderIn(BaseModel):
    traffic_gb: int
    days: int
    device_limit: int


class MiniAppCustomQuoteIn(BaseModel):
    traffic_gb: int
    days: int
    device_limit: int


@router.post("/auth")
async def miniapp_auth(
    body: MiniAppAuthIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    tg_user = validate_webapp_init_data(body.init_data, settings.telegram_bot_token)
    telegram_id = int(tg_user["id"])
    username = tg_user.get("username")
    user = await get_or_create_telegram_user(db, telegram_id, username, settings)
    await db.commit()
    token = create_access_token(user.id, settings)
    sub = await get_active_subscription(db, user.id)
    sub_data = await serialize_subscription_with_devices(db, sub, settings, include_devices=True)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserOut(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
            subscription=sub_data,  # type: ignore[arg-type]
            proxy=None,
        ),
        "miniapp_url": settings.miniapp_url,
        "casino_enabled": settings.casino_enabled,
        "support_telegram": settings.support_telegram,
        "brand_name": settings.brand_name,
    }


@router.post("/trial")
async def miniapp_trial(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    sub = await create_trial(db, user, settings)
    if not sub:
        raise HTTPException(status_code=400, detail="Trial unavailable (already used or disabled)")
    return {
        "ok": True,
        "subscription": await serialize_subscription_with_devices(db, sub, settings, include_devices=True),
    }


@router.post("/orders")
async def miniapp_create_order(
    body: MiniAppOrderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    plan = await db.get(Plan, body.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found")
    order = await create_order(db, user, plan)
    provider = YooMoneyProvider(settings)
    redirect = provider.create_payment(order, description=f"{settings.brand_name}: {plan.name}")
    return {
        "id": str(order.id),
        "amount": float(order.amount),
        "payment_label": order.payment_label,
        "payment_url": redirect.payment_url,
        "title": plan.name,
    }


@router.post("/orders/custom/quote")
async def miniapp_custom_quote(
    body: MiniAppCustomQuoteIn,
    _: User = Depends(get_current_user),
) -> dict:
    try:
        return custom_price_breakdown(
            traffic_gb=body.traffic_gb,
            days=body.days,
            device_limit=body.device_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/custom")
async def miniapp_custom_order(
    body: MiniAppCustomOrderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
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
    redirect = provider.create_payment(order, description=f"{settings.brand_name}: {breakdown['title']}")
    return {
        "id": str(order.id),
        "amount": float(order.amount),
        "payment_label": order.payment_label,
        "payment_url": redirect.payment_url,
        "title": breakdown["title"],
    }


@router.get("/casino/status")
async def casino_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    sub = await get_active_subscription(db, user.id)
    eligible, message = casino_eligible(sub)
    return {
        "enabled": settings.casino_enabled,
        "eligible": eligible and settings.casino_enabled,
        "message": message if settings.casino_enabled else "Казино выключено.",
        "bet_days": BET_DAYS,
        "bet_fixed": True,
        "rtp": books_rtp(),
        "books": BOOK_COUNT,
        "max_win_days": MAX_WIN_DAYS,
        "lines": 5,
        "grid": "3x3",
        "paytable": paytable_public(),
        "subscription": await serialize_subscription_with_devices(db, sub, settings, include_devices=True)
        if sub
        else None,
    }


@router.post("/casino/spin")
async def casino_spin(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    result = await spin_casino(db, user=user, settings=settings)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "ok": True,
        "bet_days": result.bet_days,
        "win_days": result.win_days,
        "net_days": result.net_days,
        "grid": result.grid,
        "winning_lines": result.winning_lines,
        "book_index": result.book_index,
        "days_left": result.days_left,
        "subscription": result.subscription,
        "max_win_days": MAX_WIN_DAYS,
        "is_bonus": result.is_bonus,
        "bonus_spins": len(result.bonus_rounds),
        "bonus_rounds": result.bonus_rounds,
        "message": (
            "Bonus! 7 спинов"
            if result.is_bonus
            else (f"Выигрыш: +{result.win_days} дн." if result.win_days > 0 else "Не повезло — день списан.")
        ),
    }
