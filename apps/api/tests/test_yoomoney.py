from __future__ import annotations

import hashlib

from app.config import Settings
from app.services.yoomoney import YooMoneyProvider


def test_yoomoney_hash_ok() -> None:
    settings = Settings(
        yoomoney_wallet="410011111111111",
        yoomoney_notification_secret="secret123",
    )
    form = {
        "notification_type": "p2p-incoming",
        "operation_id": "1234567",
        "amount": "100.00",
        "currency": "643",
        "datetime": "2026-08-03T12:00:00Z",
        "sender": "410022222222222",
        "codepro": "false",
        "label": "abcLABEL",
    }
    check = "&".join(
        [
            form["notification_type"],
            form["operation_id"],
            form["amount"],
            form["currency"],
            form["datetime"],
            form["sender"],
            form["codepro"],
            "secret123",
            form["label"],
        ]
    )
    form["sha1_hash"] = hashlib.sha1(check.encode()).hexdigest()
    result = YooMoneyProvider(settings).verify_notification(form)
    assert result.success is True
    assert result.external_id == "1234567"
    assert result.label == "abcLABEL"


def test_yoomoney_hash_bad() -> None:
    settings = Settings(yoomoney_notification_secret="secret123")
    form = {
        "notification_type": "p2p-incoming",
        "operation_id": "1",
        "amount": "10.00",
        "currency": "643",
        "datetime": "2026-08-03T12:00:00Z",
        "sender": "4100",
        "codepro": "false",
        "label": "x",
        "sha1_hash": "deadbeef",
    }
    result = YooMoneyProvider(settings).verify_notification(form)
    assert result.success is False


def test_yoomoney_sign_ok() -> None:
    import hmac
    from urllib.parse import quote

    settings = Settings(yoomoney_notification_secret="secret123")
    form = {
        "notification_type": "p2p-incoming",
        "operation_id": "999",
        "amount": "100.00",
        "currency": "643",
        "datetime": "2026-08-03T12:00:00Z",
        "sender": "410022222222222",
        "codepro": "false",
        "label": "abcLABEL",
    }
    parts = [f"{k}={quote(form[k], safe='')}" for k in sorted(form)]
    payload = "&".join(parts)
    form["sign"] = hmac.new(b"secret123", payload.encode(), hashlib.sha256).hexdigest()
    result = YooMoneyProvider(settings).verify_notification(form)
    assert result.success is True
    assert result.label == "abcLABEL"
