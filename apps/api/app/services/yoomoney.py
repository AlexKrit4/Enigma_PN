from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlencode

from fastapi import Request

from app.config import Settings, get_settings
from app.models.entities import Order


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
        # Also allow AC (card) — user can switch on YooMoney form; SB = SBP default
        url = f"https://yoomoney.ru/quickpay/confirm.xml?{urlencode(params)}"
        return PaymentRedirect(payment_url=url, label=order.payment_label)

    def verify_notification(self, form: dict[str, str]) -> PaymentResult:
        """
        Verify YooMoney HTTP notification hash.

        sha1_hash = sha1(
          notification_type&operation_id&amount&currency&datetime&sender&codepro&notification_secret&label
        )
        """
        required = [
            "notification_type",
            "operation_id",
            "amount",
            "currency",
            "datetime",
            "sender",
            "codepro",
            "sha1_hash",
            "label",
        ]
        missing = [k for k in required if k not in form]
        if missing:
            return PaymentResult(
                success=False,
                external_id=form.get("operation_id", ""),
                label=form.get("label", ""),
                amount=Decimal("0"),
                raw=form,
                error=f"missing fields: {missing}",
            )

        secret = self.settings.yoomoney_notification_secret
        if not secret:
            return PaymentResult(
                success=False,
                external_id=form["operation_id"],
                label=form["label"],
                amount=Decimal(form["amount"]),
                raw=form,
                error="YOOMONEY_NOTIFICATION_SECRET not configured",
            )

        check_string = "&".join(
            [
                form["notification_type"],
                form["operation_id"],
                form["amount"],
                form["currency"],
                form["datetime"],
                form["sender"],
                form["codepro"],
                secret,
                form["label"],
            ]
        )
        expected = hashlib.sha1(check_string.encode("utf-8")).hexdigest()
        if expected.lower() != form["sha1_hash"].lower():
            return PaymentResult(
                success=False,
                external_id=form["operation_id"],
                label=form["label"],
                amount=Decimal(form["amount"]),
                raw=form,
                error="invalid sha1_hash",
            )

        if form.get("codepro", "false").lower() == "true":
            return PaymentResult(
                success=False,
                external_id=form["operation_id"],
                label=form["label"],
                amount=Decimal(form["amount"]),
                raw=form,
                error="code-protected transfer ignored",
            )

        return PaymentResult(
            success=True,
            external_id=form["operation_id"],
            label=form["label"],
            amount=Decimal(form["amount"]),
            raw=form,
        )

    async def parse_request(self, request: Request) -> dict[str, str]:
        form = await request.form()
        return {k: str(v) for k, v in form.items()}
