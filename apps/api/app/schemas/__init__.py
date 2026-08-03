from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    group_name: str
    duration_days: int
    traffic_gb: int | None
    device_limit: int
    price_rub: Decimal
    is_active: bool
    sort_order: int


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    starts_at: datetime
    ends_at: datetime
    traffic_limit_gb: int | None
    traffic_used_gb: Decimal
    device_limit: int
    sub_url: str | None = None
    happ_deep_link: str | None = None
    plan: PlanOut | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    telegram_id: int | None
    username: str | None
    email: str | None
    is_admin: bool
    created_at: datetime
    subscription: SubscriptionOut | None = None


class TelegramAuthIn(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    init_data: str | None = None


class OrderCreateIn(BaseModel):
    plan_id: uuid.UUID
    telegram_id: int | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    amount: Decimal
    currency: str
    payment_provider: str
    payment_label: str
    payment_url: str | None = None
    created_at: datetime
    paid_at: datetime | None


class TrialCreateIn(BaseModel):
    telegram_id: int
    username: str | None = None


class AdminExtendIn(BaseModel):
    days: int = Field(gt=0, le=3650)


class AdminGrantIn(BaseModel):
    days: int = Field(gt=0, le=3650)
    traffic_gb: int | None = Field(default=None, ge=0)
    device_limit: int | None = Field(default=None, ge=1, le=50)
    username: str | None = None


class StatsOut(BaseModel):
    users_total: int
    subscriptions_active: int
    subscriptions_trial: int
    orders_paid: int
    mrr_rub: Decimal
