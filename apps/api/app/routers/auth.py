from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import create_access_token, get_current_user, get_or_create_telegram_user, require_bot
from app.models.entities import User
from app.schemas import TelegramAuthIn, TrialCreateIn, UserOut
from app.services.provisioning import (
    create_trial,
    get_active_subscription,
    serialize_subscription_with_devices,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/telegram")
async def auth_telegram(
    body: TelegramAuthIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_bot),
) -> dict:
    user = await get_or_create_telegram_user(db, body.telegram_id, body.username, settings)
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
        ),
    }


@router.get("/me", response_model=UserOut)
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserOut:
    sub = await get_active_subscription(db, user.id)
    sub_data = await serialize_subscription_with_devices(db, sub, settings, include_devices=True)
    return UserOut(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at,
        subscription=sub_data,  # type: ignore[arg-type]
    )


@router.post("/trial")
async def start_trial(
    body: TrialCreateIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_bot),
) -> dict:
    user = await get_or_create_telegram_user(db, body.telegram_id, body.username, settings)
    await db.commit()
    sub = await create_trial(db, user, settings)
    if not sub:
        raise HTTPException(status_code=400, detail="Trial unavailable (already used or disabled)")
    return {
        "ok": True,
        "subscription": await serialize_subscription_with_devices(db, sub, settings, include_devices=True),
    }
