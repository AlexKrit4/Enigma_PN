from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from app.config import Settings, get_settings


@dataclass(frozen=True)
class TelegramProxyLinks:
    enabled: bool
    host: str
    port: int
    secret: str
    tg_url: str
    https_url: str
    ready: bool
    message: str


def build_telegram_proxy_links(settings: Settings | None = None) -> TelegramProxyLinks:
    settings = settings or get_settings()
    host = (settings.mtproto_host or "").strip()
    secret = (settings.mtproto_secret or "").strip()
    port = int(settings.mtproto_port)
    enabled = bool(settings.mtproto_enabled)

    if not enabled:
        return TelegramProxyLinks(
            enabled=False,
            host=host,
            port=port,
            secret=secret,
            tg_url="",
            https_url="",
            ready=False,
            message="MTProto proxy выключен (MTPROTO_ENABLED=false).",
        )

    if not host or not secret:
        return TelegramProxyLinks(
            enabled=True,
            host=host,
            port=port,
            secret=secret,
            tg_url="",
            https_url="",
            ready=False,
            message="Прокси ещё не настроен: укажите MTPROTO_HOST и MTPROTO_SECRET.",
        )

    query = urlencode({"server": host, "port": str(port), "secret": secret})
    tg_url = f"tg://proxy?{query}"
    https_url = f"https://t.me/proxy?{query}"
    return TelegramProxyLinks(
        enabled=True,
        host=host,
        port=port,
        secret=secret,
        tg_url=tg_url,
        https_url=https_url,
        ready=True,
        message="OK",
    )
