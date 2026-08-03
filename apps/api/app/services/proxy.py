from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.entities import Plan, ProxyAccess, SubscriptionStatus, User
from app.services.telegram_notify import send_telegram_message


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_proxy_kind(plan: Plan | None, meta: dict | None = None) -> bool:
    kind = ""
    if meta and meta.get("kind"):
        kind = str(meta.get("kind"))
    elif plan is not None:
        kind = str(plan.group_name or "")
    kind_l = kind.strip().lower()
    return kind_l in {"прокси", "proxy", "mtproto"}


def proxy_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.mtproto_enabled and settings.mtproto_host and settings.mtproto_secret and settings.mtproto_port)


def build_proxy_links(settings: Settings | None = None) -> dict[str, str]:
    settings = settings or get_settings()
    host = settings.mtproto_host
    port = int(settings.mtproto_port)
    secret = settings.mtproto_secret
    qs = f"server={quote(host)}&port={port}&secret={quote(secret)}"
    return {
        "host": host,
        "port": str(port),
        "secret": secret,
        "tg_url": f"tg://proxy?{qs}",
        "https_url": f"https://t.me/proxy?{qs}",
    }


async def get_proxy_access(db: AsyncSession, user_id: UUID) -> ProxyAccess | None:
    result = await db.execute(select(ProxyAccess).where(ProxyAccess.user_id == user_id))
    access = result.scalar_one_or_none()
    if not access:
        return None
    if access.status == SubscriptionStatus.active and access.ends_at <= _now():
        access.status = SubscriptionStatus.expired
        await db.flush()
    return access


async def get_active_proxy_access(db: AsyncSession, user_id: UUID) -> ProxyAccess | None:
    access = await get_proxy_access(db, user_id)
    if not access:
        return None
    if access.status == SubscriptionStatus.active and access.ends_at > _now():
        return access
    return None


def serialize_proxy_access(
    access: ProxyAccess | None,
    settings: Settings | None = None,
    *,
    include_credentials: bool = True,
) -> dict | None:
    if not access:
        return None
    settings = settings or get_settings()
    active = access.status == SubscriptionStatus.active and access.ends_at > _now()
    data: dict = {
        "id": str(access.id),
        "status": access.status.value if active else (
            access.status.value if access.status != SubscriptionStatus.active else SubscriptionStatus.expired.value
        ),
        "starts_at": access.starts_at.isoformat() if access.starts_at else None,
        "ends_at": access.ends_at.isoformat() if access.ends_at else None,
        "active": active,
        "title": "MTProto прокси",
    }
    if include_credentials and active and proxy_configured(settings):
        data.update(build_proxy_links(settings))
    return data


async def grant_or_extend_proxy(
    db: AsyncSession,
    *,
    user: User,
    days: int,
    order_id: UUID | None = None,
    stack: bool = True,
) -> ProxyAccess:
    if days < 1:
        raise ValueError("days must be >= 1")
    now = _now()
    access = await get_proxy_access(db, user.id)
    if access:
        if stack and access.status == SubscriptionStatus.active and access.ends_at > now:
            access.ends_at = access.ends_at + timedelta(days=days)
        else:
            access.starts_at = now
            access.ends_at = now + timedelta(days=days)
        access.status = SubscriptionStatus.active
        if order_id:
            access.order_id = order_id
        access.updated_at = now
        await db.flush()
        return access

    access = ProxyAccess(
        user_id=user.id,
        status=SubscriptionStatus.active,
        starts_at=now,
        ends_at=now + timedelta(days=days),
        order_id=order_id,
    )
    db.add(access)
    await db.flush()
    return access


async def revoke_proxy_access(db: AsyncSession, *, user: User) -> ProxyAccess | None:
    access = await get_proxy_access(db, user.id)
    if not access:
        return None
    access.status = SubscriptionStatus.disabled
    access.ends_at = _now()
    access.updated_at = _now()
    await db.flush()
    return access


async def notify_proxy_ready(
    db: AsyncSession,
    *,
    user: User,
    access: ProxyAccess,
    title: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if not user.telegram_id:
        return
    data = serialize_proxy_access(access, settings, include_credentials=True) or {}
    ends = access.ends_at
    ends_label = f"{ends.day:02d}.{ends.month:02d}.{ends.year}"
    text = (
        f"✅ <b>{title}</b>\n\n"
        f"Тариф: <b>MTProto прокси</b>\n"
        f"Действует до: <b>{ends_label}</b>\n"
        f"Привязка: <b>ваш аккаунт в боте</b>\n\n"
        "Откройте раздел «🔌 Прокси» или нажмите кнопку ниже."
    )
    markup = None
    https_url = data.get("https_url")
    if https_url:
        markup = {"inline_keyboard": [[{"text": "🔌 Добавить в Telegram", "url": https_url}]]}
    await send_telegram_message(int(user.telegram_id), text, settings=settings, reply_markup=markup)


async def expire_due_proxy_access(db: AsyncSession) -> int:
    now = _now()
    result = await db.execute(
        select(ProxyAccess).where(
            ProxyAccess.status == SubscriptionStatus.active,
            ProxyAccess.ends_at <= now,
        )
    )
    rows = list(result.scalars().all())
    for row in rows:
        row.status = SubscriptionStatus.expired
        row.updated_at = now
    if rows:
        await db.flush()
    return len(rows)
