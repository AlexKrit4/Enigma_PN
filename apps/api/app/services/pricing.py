from __future__ import annotations

from decimal import Decimal

from app.models.entities import Plan

CUSTOM_PRICE_PER_GB = 2
CUSTOM_PRICE_PER_DAY = 1
CUSTOM_PRICE_PER_DEVICE = 25

CUSTOM_MIN_GB = 1
CUSTOM_MAX_GB = 10_000
CUSTOM_MIN_DAYS = 1
CUSTOM_MAX_DAYS = 3650
CUSTOM_MIN_DEVICES = 1
CUSTOM_MAX_DEVICES = 20


def calc_custom_price(*, traffic_gb: int, days: int, device_limit: int) -> Decimal:
    total = (
        traffic_gb * CUSTOM_PRICE_PER_GB
        + days * CUSTOM_PRICE_PER_DAY
        + device_limit * CUSTOM_PRICE_PER_DEVICE
    )
    return Decimal(total).quantize(Decimal("0.01"))


def validate_custom_tariff(*, traffic_gb: int, days: int, device_limit: int) -> None:
    if traffic_gb < CUSTOM_MIN_GB or traffic_gb > CUSTOM_MAX_GB:
        raise ValueError(f"traffic_gb must be {CUSTOM_MIN_GB}…{CUSTOM_MAX_GB} (unlimited not allowed)")
    if days < CUSTOM_MIN_DAYS or days > CUSTOM_MAX_DAYS:
        raise ValueError(f"days must be {CUSTOM_MIN_DAYS}…{CUSTOM_MAX_DAYS}")
    if device_limit < CUSTOM_MIN_DEVICES or device_limit > CUSTOM_MAX_DEVICES:
        raise ValueError(f"device_limit must be {CUSTOM_MIN_DEVICES}…{CUSTOM_MAX_DEVICES}")


def custom_price_breakdown(*, traffic_gb: int, days: int, device_limit: int) -> dict:
    validate_custom_tariff(traffic_gb=traffic_gb, days=days, device_limit=device_limit)
    gb_cost = traffic_gb * CUSTOM_PRICE_PER_GB
    days_cost = days * CUSTOM_PRICE_PER_DAY
    devices_cost = device_limit * CUSTOM_PRICE_PER_DEVICE
    total = calc_custom_price(traffic_gb=traffic_gb, days=days, device_limit=device_limit)
    return {
        "traffic_gb": traffic_gb,
        "days": days,
        "device_limit": device_limit,
        "gb_unit_price": CUSTOM_PRICE_PER_GB,
        "day_unit_price": CUSTOM_PRICE_PER_DAY,
        "device_unit_price": CUSTOM_PRICE_PER_DEVICE,
        "gb_cost": gb_cost,
        "days_cost": days_cost,
        "devices_cost": devices_cost,
        "total": float(total),
        "title": f"Свой тариф · {traffic_gb} ГБ · {days} дн. · {device_limit} устр.",
    }


def plan_meta(plan: Plan) -> dict:
    return {
        "duration_days": plan.duration_days,
        "traffic_gb": plan.traffic_gb,
        "device_limit": plan.device_limit,
        "title": plan.name,
        "kind": plan.group_name,
        "slug": plan.slug,
    }


def order_terms(order_meta: dict | None, plan: Plan | None) -> dict:
    meta = order_meta or {}
    if meta.get("duration_days") is not None:
        return {
            "duration_days": int(meta["duration_days"]),
            "traffic_gb": meta.get("traffic_gb"),
            "device_limit": int(meta.get("device_limit") or 1),
            "title": str(meta.get("title") or (plan.name if plan else "Подписка")),
        }
    if not plan:
        raise ValueError("Plan/terms not found")
    return {
        "duration_days": plan.duration_days,
        "traffic_gb": plan.traffic_gb,
        "device_limit": plan.device_limit,
        "title": plan.name,
    }
