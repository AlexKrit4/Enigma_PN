from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Subscription, SubscriptionDevice


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def list_devices(session: AsyncSession, subscription_id: UUID) -> list[SubscriptionDevice]:
    result = await session.execute(
        select(SubscriptionDevice)
        .where(SubscriptionDevice.subscription_id == subscription_id)
        .order_by(SubscriptionDevice.last_seen_at.desc())
    )
    return list(result.scalars().all())


async def active_device_count(session: AsyncSession, subscription_id: UUID) -> int:
    result = await session.execute(
        select(SubscriptionDevice).where(
            SubscriptionDevice.subscription_id == subscription_id,
            SubscriptionDevice.is_blocked.is_(False),
        )
    )
    return len(list(result.scalars().all()))


async def touch_device(
    session: AsyncSession,
    *,
    subscription: Subscription,
    hwid: str,
    device_os: str | None = None,
    device_model: str | None = None,
    user_agent: str | None = None,
) -> tuple[SubscriptionDevice | None, str | None]:
    """Register/update device. Returns (device, error_code).

    error_code:
      - blocked
      - limit_reached
    """
    hwid = (hwid or "").strip()
    if not hwid:
        return None, None

    result = await session.execute(
        select(SubscriptionDevice).where(
            SubscriptionDevice.subscription_id == subscription.id,
            SubscriptionDevice.hwid == hwid,
        )
    )
    device = result.scalar_one_or_none()
    now = _now()

    if device and device.is_blocked:
        return device, "blocked"

    if device is None:
        active = await active_device_count(session, subscription.id)
        limit = subscription.device_limit or 0
        if limit > 0 and active >= limit:
            return None, "limit_reached"
        device = SubscriptionDevice(
            subscription_id=subscription.id,
            hwid=hwid,
            device_os=(device_os or "")[:64] or None,
            device_model=(device_model or "")[:128] or None,
            user_agent=(user_agent or "")[:255] or None,
            first_seen_at=now,
            last_seen_at=now,
            is_blocked=False,
        )
        session.add(device)
    else:
        device.last_seen_at = now
        if device_os:
            device.device_os = device_os[:64]
        if device_model:
            device.device_model = device_model[:128]
        if user_agent:
            device.user_agent = user_agent[:255]

    await session.commit()
    await session.refresh(device)
    return device, None


async def kick_device(
    session: AsyncSession,
    *,
    subscription_id: UUID,
    device_id: UUID,
) -> SubscriptionDevice | None:
    """Remove device so the slot can be reused by another device."""
    result = await session.execute(
        select(SubscriptionDevice).where(
            SubscriptionDevice.id == device_id,
            SubscriptionDevice.subscription_id == subscription_id,
        )
    )
    device = result.scalar_one_or_none()
    if device is None:
        return None
    await session.delete(device)
    await session.commit()
    return device


def device_label(device: SubscriptionDevice) -> str:
    parts: list[str] = []
    if device.device_model:
        parts.append(device.device_model)
    if device.device_os:
        parts.append(device.device_os)
    if not parts:
        short = device.hwid[:10] + ("…" if len(device.hwid) > 10 else "")
        parts.append(f"устройство {short}")
    return " · ".join(parts)


def serialize_device(device: SubscriptionDevice) -> dict:
    return {
        "id": str(device.id),
        "hwid": device.hwid,
        "label": device_label(device),
        "device_os": device.device_os,
        "device_model": device.device_model,
        "is_blocked": device.is_blocked,
        "first_seen_at": device.first_seen_at.isoformat() if device.first_seen_at else None,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
    }
