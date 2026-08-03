from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import quote, urlencode

import structlog
from fastapi import Request

from app.config import Settings, get_settings
from app.models.entities import Order

log = structlog.get_logger(__name__)


@dataclass
class PaymentRedirect:
    payment_url: str
    label: str


@dataclass
class PaymentResult:
    success: bool
    external_id: str
    label: str
    amount: Decimal
    raw: dict
    error: str | None = None


class YooMoneyProvider:
    """YooMoney wallet payments via quickpay + HTTP notifications."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def create_payment(self, order: Order, description: str) -> PaymentRedirect:
        if not self.settings.yoomoney_wallet:
            # Dev fallback: mock payment page on API
            url = f"https://{self.settings.api_domain}/pay/mock/{order.id}?label={order.payment_label}"
            return PaymentRedirect(payment_url=url, label=order.payment_label)

        params = {
            "receiver": self.settings.yoomoney_wallet,
            "quickpay-form": "shop",
            "targets": description,
            "paymentType": "SB",
            "sum": f"{order.amount:.2f}",
            "label": order.payment_label,
            "successURL": f"https://{self.settings.web_domain}/dashboard?paid=1",
        }
        url = f"https://yoomoney.ru/quickpay/confirm.xml?{urlencode(params)}"
        return PaymentRedirect(payment_url=url, label=order.payment_label)

    def _verify_sha1(self, form: dict[str, str], secret: str) -> bool:
        check_string = "&".join(
            [
                form.get("notification_type", ""),
                form.get("operation_id", ""),
                form.get("amount", ""),
                form.get("currency", ""),
                form.get("datetime", ""),
                form.get("sender", ""),
                form.get("codepro", ""),
                secret,
                form.get("label", ""),
            ]
        )
        expected = hashlib.sha1(check_string.encode("utf-8")).hexdigest()
        got = form.get("sha1_hash", "")
        ok = bool(got) and expected.lower() == got.lower()
        if not ok:
            log.warning(
                "yoomoney_sha1_mismatch",
                expected=expected,
                got=got,
                label=form.get("label"),
                operation_id=form.get("operation_id"),
            )
        return ok

    def _verify_sign(self, form: dict[str, str], secret: str) -> bool:
        """HMAC-SHA256 `sign` (current YooMoney verification)."""
        got = form.get("sign", "")
        if not got:
            return False
        parts = [
            f"{key}={quote(str(form.get(key, '')), safe='')}"
            for key in sorted(k for k in form.keys() if k != "sign")
        ]
        payload = "&".join(parts)
        expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        ok = hmac.compare_digest(expected.lower(), got.lower())
        if not ok:
            log.warning(
                "yoomoney_sign_mismatch",
                expected=expected,
                got=got,
                label=form.get("label"),
                operation_id=form.get("operation_id"),
                keys=sorted(form.keys()),
            )
        return ok

    def verify_notification(self, form: dict[str, str]) -> PaymentResult:
        """
        Verify YooMoney HTTP notification.

        Prefer modern `sign` (HMAC-SHA256). Fall back to legacy `sha1_hash`.
        """
        label = form.get("label", "")
        operation_id = form.get("operation_id", "")
        amount_raw = form.get("amount", "0") or "0"

        secret = self.settings.yoomoney_notification_secret
        if not secret:
            return PaymentResult(
                success=False,
                external_id=operation_id,
                label=label,
                amount=Decimal(amount_raw),
                raw=form,
                error="YOOMONEY_NOTIFICATION_SECRET not configured",
            )

        if not operation_id or "amount" not in form:
            return PaymentResult(
                success=False,
                external_id=operation_id,
                label=label,
                amount=Decimal("0"),
                raw=form,
                error="missing operation_id or amount",
            )

        signed_ok = self._verify_sign(form, secret) or self._verify_sha1(form, secret)
        if not signed_ok:
            return PaymentResult(
                success=False,
                external_id=operation_id,
                label=label,
                amount=Decimal(amount_raw),
                raw=form,
                error="invalid signature (sign/sha1_hash)",
            )

        if form.get("codepro", "false").lower() == "true":
            return PaymentResult(
                success=False,
                external_id=operation_id,
                label=label,
                amount=Decimal(amount_raw),
                raw=form,
                error="code-protected transfer ignored",
            )

        return PaymentResult(
            success=True,
            external_id=operation_id,
            label=label,
            amount=Decimal(amount_raw),
            raw=form,
        )

    async def parse_request(self, request: Request) -> dict[str, str]:
        form = await request.form()
        return {k: str(v) for k, v in form.items()}
