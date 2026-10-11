"""Pricing for the public website tariff (single plan, period discounts, paid extra devices)."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal

SITE_PLAN_SLUG = "site-bypass"
SITE_PLAN_NAME = "Обход белых списков"
SITE_PLAN_GROUP = "сайт"
SITE_BASE_DEVICES = 5
SITE_EXTRA_DEVICE_PRICE_PER_MONTH = 50
SITE_MAX_DEVICES = 50
SITE_TRIAL_DAYS = 1

# months -> price in RUB for the base tariff (5 devices, unlimited traffic)
SITE_PERIODS: dict[int, int] = {1: 200, 3: 550, 6: 1050, 12: 2000}


def period_days(months: int) -> int:
    return months * 30


def base_price(months: int) -> int:
    if months not in SITE_PERIODS:
        raise ValueError("unsupported period")
    return SITE_PERIODS[months]


def extra_devices_price(extra_devices: int, months: int) -> int:
    return extra_devices * months * SITE_EXTRA_DEVICE_PRICE_PER_MONTH


def validate_devices(total_devices: int) -> None:
    if total_devices < SITE_BASE_DEVICES or total_devices > SITE_MAX_DEVICES:
        raise ValueError(f"devices must be {SITE_BASE_DEVICES}…{SITE_MAX_DEVICES}")


def quote_subscription(months: int, extra_devices: int) -> dict:
    validate_devices(SITE_BASE_DEVICES + extra_devices)
    base = base_price(months)
    extra = extra_devices_price(extra_devices, months)
    total = base + extra
    devices = SITE_BASE_DEVICES + extra_devices
    title = f"{SITE_PLAN_NAME} · {months} мес. · {devices} устр."
    return {
        "months": months,
        "days": period_days(months),
        "devices": devices,
        "extra_devices": extra_devices,
        "base_price": base,
        "extra_price": extra,
        "total": total,
        "title": title,
    }


def remaining_months(ends_at: datetime) -> int:
    """Whole months (30 days) left on a subscription, rounded up, at least 1."""
    now = datetime.now(timezone.utc)
    left_days = (ends_at - now).total_seconds() / 86400
    return max(1, math.ceil(left_days / 30))


def quote_extra_devices(extra_devices: int, current_devices: int, ends_at: datetime) -> dict:
    validate_devices(current_devices + extra_devices)
    months = remaining_months(ends_at)
    total = extra_devices_price(extra_devices, months)
    return {
        "extra_devices": extra_devices,
        "devices": current_devices + extra_devices,
        "months": months,
        "total": total,
        "title": f"+{extra_devices} устр. до конца подписки ({months} мес.)",
    }


def pricing_catalog() -> dict:
    return {
        "plan_name": SITE_PLAN_NAME,
        "base_devices": SITE_BASE_DEVICES,
        "max_devices": SITE_MAX_DEVICES,
        "extra_device_price_per_month": SITE_EXTRA_DEVICE_PRICE_PER_MONTH,
        "trial_days": SITE_TRIAL_DAYS,
        "periods": [
            {"months": m, "price": p, "per_month": round(p / m)} for m, p in sorted(SITE_PERIODS.items())
        ],
    }


def to_money(value: int) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))
