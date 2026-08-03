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


class AdminLimitsIn(BaseModel):
    traffic_gb: int | None = Field(default=None, ge=0)
    clear_traffic_limit: bool = False
    device_limit: int | None = Field(default=None, ge=1, le=50)


class AdminBroadcastIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    audience: str = Field(default="active")  # all | active


class AdminPlanIn(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    group_name: str = "для себя"
    duration_days: int = Field(gt=0, le=3650)
    traffic_gb: int | None = Field(default=None, ge=0)
    device_limit: int = Field(default=2, ge=1, le=50)
    price_rub: Decimal = Field(ge=0)
    is_active: bool = True
    sort_order: int = 0


class AdminPlanPatchIn(BaseModel):
    name: str | None = None
    group_name: str | None = None
    duration_days: int | None = Field(default=None, gt=0, le=3650)
    traffic_gb: int | None = Field(default=None, ge=0)
    device_limit: int | None = Field(default=None, ge=1, le=50)
    price_rub: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    sort_order: int | None = None


class AdminPromoIn(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    days: int = Field(default=30, gt=0, le=3650)
    traffic_gb: int | None = Field(default=None, ge=0)
    device_limit: int | None = Field(default=None, ge=1, le=50)
    max_uses: int | None = Field(default=None, ge=1)
    note: str | None = Field(default=None, max_length=255)


class StatsOut(BaseModel):
    users_total: int
    subscriptions_active: int
    subscriptions_trial: int
    orders_paid: int
    mrr_rub: Decimal
    revenue_today_rub: Decimal = Decimal("0")
    revenue_7d_rub: Decimal = Decimal("0")
    pending_orders: int = 0
