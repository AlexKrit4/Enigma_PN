from __future__ import annotations

from app.config import Settings
from app.services.telegram_proxy import build_telegram_proxy_links


def test_telegram_proxy_disabled() -> None:
    links = build_telegram_proxy_links(Settings(mtproto_enabled=False))
    assert links.enabled is False
    assert links.ready is False


def test_telegram_proxy_missing_secret() -> None:
    links = build_telegram_proxy_links(
        Settings(mtproto_enabled=True, mtproto_host="tg.bigwinzone.ru", mtproto_secret="")
    )
    assert links.enabled is True
    assert links.ready is False


def test_telegram_proxy_links() -> None:
    secret = "ee0123456789abcdef0123456789abcdef676f6f676c652e636f6d"
    links = build_telegram_proxy_links(
        Settings(
            mtproto_enabled=True,
            mtproto_host="tg.bigwinzone.ru",
            mtproto_port=8443,
            mtproto_secret=secret,
        )
    )
    assert links.ready is True
    assert links.tg_url.startswith("tg://proxy?")
    assert "server=tg.bigwinzone.ru" in links.tg_url
    assert "port=8443" in links.tg_url
    assert secret in links.tg_url
    assert links.https_url.startswith("https://t.me/proxy?")
