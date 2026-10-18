"""Отправка писем с кодом подтверждения: Resend HTTPS API или SMTP (smtplib в threadpool)."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

import httpx
import structlog

from app.config import Settings, get_settings

log = structlog.get_logger(__name__)


def smtp_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def _is_resend(settings: Settings) -> bool:
    return settings.smtp_host.rstrip(".").lower() == "smtp.resend.com"


async def _send_resend(settings: Settings, to_addr: str, subject: str, body: str) -> None:
    """Resend HTTPS API — используется, когда провайдер блокирует исходящие SMTP-порты."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.smtp_password}"},
            json={
                "from": settings.smtp_from or settings.smtp_user,
                "to": [to_addr],
                "subject": subject,
                "text": body,
            },
        )
        resp.raise_for_status()


def _send_smtp(settings: Settings, to_addr: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    if settings.smtp_starttls or settings.smtp_port == 587:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)


async def send_verification_code(email: str, code: str, settings: Settings | None = None) -> bool:
    """Отправить код на почту. Без SMTP-настроек — пишет код в лог и возвращает False."""
    settings = settings or get_settings()
    brand = settings.brand_name
    subject = f"{brand}: код подтверждения"
    body = (
        f"Ваш код подтверждения: {code}\n\n"
        f"Введите его на сайте, чтобы активировать пробный период. "
        f"Код действует 10 минут.\n\n"
        f"Если вы не регистрировались на {settings.web_domain}, просто удалите это письмо.\n\n"
        f"— {brand}"
    )
    if not smtp_configured(settings):
        log.warning("smtp_not_configured_code_logged", email=email, code=code)
        return False
    try:
        if _is_resend(settings):
            await _send_resend(settings, email, subject, body)
        else:
            await asyncio.to_thread(_send_smtp, settings, email, subject, body)
        log.info("verification_email_sent", email=email)
        return True
    except Exception as exc:
        log.error("verification_email_failed", email=email, error=str(exc))
        raise
