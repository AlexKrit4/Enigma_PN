from __future__ import annotations

import json
import logging
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.entities import Plan, ProxyAccess, SubscriptionStatus, User
from app.services.telegram_notify import send_telegram_message

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_proxy_kind(plan: Plan | None, meta: dict | None = None) -> bool:
    kind = ""
    if meta and meta.get("kind"):
        kind = str(meta.get("kind"))
    elif plan is not None:
        kind = str(plan.group_name or "")
    kind_l = kind.strip().lower()
    return kind_l in {"прокси", "proxy", "mtproto", "socks", "socks5"}


def proxy_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.socks5_enabled and settings.socks5_host and settings.socks5_port)


def _new_socks_username(user: User) -> str:
    if user.telegram_id:
        return f"tg{int(user.telegram_id)}"
    return f"u{secrets.token_hex(4)}"


def _new_socks_password() -> str:
    return secrets.token_hex(8)


def ensure_socks_credentials(access: ProxyAccess, user: User, *, rotate: bool = False) -> bool:
    """Ensure access has SOCKS login. Returns True if credentials changed."""
    changed = False
    if not access.socks_username:
        access.socks_username = _new_socks_username(user)
        changed = True
    if rotate or not access.socks_password:
        access.socks_password = _new_socks_password()
        changed = True
    return changed


def build_proxy_links(
    *,
    username: str,
    password: str,
    settings: Settings | None = None,
) -> dict[str, str]:
    settings = settings or get_settings()
    host = settings.socks5_host
    port = int(settings.socks5_port)
    qs = (
        f"server={quote(host)}&port={port}"
        f"&user={quote(username)}&pass={quote(password)}"
    )
    return {
        "host": host,
        "port": str(port),
        "username": username,
        "password": password,
        "secret": "",
        "tg_url": f"tg://socks?{qs}",
        "https_url": f"https://t.me/socks?{qs}",
    }


def _socks_dir(settings: Settings) -> Path:
    return Path(settings.socks5_passwd_path).expanduser().resolve().parent


def write_socks_config(rows: list[ProxyAccess], settings: Settings | None = None) -> int:
    """Write sing-box SOCKS5 config with per-user auth (and legacy 3proxy passwd)."""
    settings = settings or get_settings()
    directory = _socks_dir(settings)
    directory.mkdir(parents=True, exist_ok=True)

    users: list[dict[str, str]] = []
    passwd_lines: list[str] = []
    for row in rows:
        username = (row.socks_username or "").replace(":", "").strip()
        password = (row.socks_password or "").replace(":", "").strip()
        if username and password:
            users.append({"username": username, "password": password})
            passwd_lines.append(f"{username}:CL:{password}")

    # Never expose an open SOCKS without auth.
    if not users:
        noop_pass = secrets.token_hex(16)
        users = [{"username": "_noop", "password": noop_pass}]
        passwd_lines = [f"_noop:CL:{noop_pass}"]

    config = {
        "log": {"level": "info", "timestamp": True},
        "inbounds": [
            {
                "type": "socks",
                "tag": "socks-in",
                "listen": settings.socks5_listen_host or "127.0.0.1",
                "listen_port": int(settings.socks5_listen_port or 40080),
                "users": users,
            }
        ],
        "outbounds": [{"type": "direct", "tag": "direct"}],
    }

    cfg_path = directory / "config.json"
    tmp_cfg = cfg_path.with_suffix(".tmp")
    tmp_cfg.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_cfg.replace(cfg_path)

    passwd_path = Path(settings.socks5_passwd_path)
    tmp_pw = passwd_path.with_suffix(".tmp")
    tmp_pw.write_text("\n".join(passwd_lines) + "\n", encoding="utf-8")
    tmp_pw.replace(passwd_path)

    return len([u for u in users if u["username"] != "_noop"])


def reload_socks_proxy(settings: Settings | None = None) -> None:
    """Touch reload stamp so host /opt/socks5/watch.sh restarts sing-box."""
    settings = settings or get_settings()
    stamp = _socks_dir(settings) / "passwd.reload"
    try:
        stamp.write_text(str(_now().timestamp()), encoding="utf-8")
    except OSError as exc:
        log.warning("socks5 reload stamp failed: %s", exc)
    name = (settings.socks5_container or "").strip()
    if not name:
        return
    # Optional: if docker CLI is available on the host-mounted environment.
    try:
        subprocess.run(
            ["docker", "restart", name],
            check=False,
            capture_output=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("socks5 docker restart skipped: %s", exc)


async def sync_socks_users(db: AsyncSession, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    if not proxy_configured(settings):
        return 0
    now = _now()
    result = await db.execute(
        select(ProxyAccess).where(
            ProxyAccess.status == SubscriptionStatus.active,
            ProxyAccess.ends_at > now,
        )
    )
    rows = list(result.scalars().all())
    count = write_socks_config(rows, settings)
    reload_socks_proxy(settings)
    return count


async def get_proxy_access(db: AsyncSession, user_id: UUID) -> ProxyAccess | None:
    result = await db.execute(select(ProxyAccess).where(ProxyAccess.user_id == user_id))
    access = result.scalar_one_or_none()
    if not access:
        return None
    if access.status == SubscriptionStatus.active and access.ends_at <= _now():
        access.status = SubscriptionStatus.expired
        await db.flush()
        await sync_socks_users(db)
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
        "title": "SOCKS5 прокси",
    }
    if (
        include_credentials
        and active
        and proxy_configured(settings)
        and access.socks_username
        and access.socks_password
    ):
        data.update(
            build_proxy_links(
                username=access.socks_username,
                password=access.socks_password,
                settings=settings,
            )
        )
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
    was_inactive = True
    if access:
        was_inactive = not (
            access.status == SubscriptionStatus.active and access.ends_at > now
        )
        if stack and access.status == SubscriptionStatus.active and access.ends_at > now:
            access.ends_at = access.ends_at + timedelta(days=days)
        else:
            access.starts_at = now
            access.ends_at = now + timedelta(days=days)
        access.status = SubscriptionStatus.active
        if order_id:
            access.order_id = order_id
        access.updated_at = now
        ensure_socks_credentials(access, user, rotate=was_inactive and bool(access.socks_password))
        await db.flush()
        await sync_socks_users(db)
        return access

    access = ProxyAccess(
        user_id=user.id,
        status=SubscriptionStatus.active,
        starts_at=now,
        ends_at=now + timedelta(days=days),
        order_id=order_id,
    )
    ensure_socks_credentials(access, user, rotate=True)
    db.add(access)
    await db.flush()
    await sync_socks_users(db)
    return access


async def revoke_proxy_access(db: AsyncSession, *, user: User) -> ProxyAccess | None:
    access = await get_proxy_access(db, user.id)
    if not access:
        return None
    access.status = SubscriptionStatus.disabled
    access.ends_at = _now()
    access.updated_at = _now()
    await db.flush()
    await sync_socks_users(db)
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
        f"Тариф: <b>SOCKS5 прокси</b>\n"
        f"Действует до: <b>{ends_label}</b>\n"
        f"Логин: <code>{data.get('username') or '—'}</code>\n"
        f"Пароль: <code>{data.get('password') or '—'}</code>\n\n"
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
        await sync_socks_users(db)
    return len(rows)


async def count_active_proxy_users(db: AsyncSession) -> int:
    now = _now()
    result = await db.execute(
        select(ProxyAccess).where(
            ProxyAccess.status == SubscriptionStatus.active,
            ProxyAccess.ends_at > now,
        )
    )
    return len(list(result.scalars().all()))
