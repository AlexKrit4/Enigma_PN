from __future__ import annotations

import httpx
import structlog

from app.config import Settings, get_settings

log = structlog.get_logger(__name__)


async def send_telegram_message(
    chat_id: int,
    text: str,
    *,
    settings: Settings | None = None,
    reply_markup: dict | None = None,
) -> bool:
    settings = settings or get_settings()
    token = settings.telegram_bot_token
    if not token or not chat_id:
        log.warning("telegram_notify_skipped", reason="missing token or chat_id")
        return False
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json=payload,
            )
            if resp.status_code >= 400:
                log.error("telegram_notify_failed", status=resp.status_code, body=resp.text[:300])
                return False
            return True
    except Exception as exc:
        log.error("telegram_notify_error", error=str(exc))
        return False
