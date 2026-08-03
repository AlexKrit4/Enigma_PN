from __future__ import annotations

import enum
import secrets
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class SubscriptionStatus(str, enum.Enum):
    trial = "trial"
    active = "active"
    expired = "expired"
    disabled = "disabled"


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _sub_token() -> str:
    return secrets.token_urlsafe(32)


def _referral_code() -> str:
    return secrets.token_urlsafe(8)[:12]


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, default=_referral_code)
    referred_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="user")
    orders: Mapped[list[Order]] = relationship(back_populates="user")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    group_name: Mapped[str] = mapped_column(String(64), default="для себя")
    duration_days: Mapped[int] = mapped_column(Integer)
    traffic_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_limit: Mapped[int] = mapped_column(Integer, default=2)
    price_rub: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    price_stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.pending)
    payment_provider: Mapped[str] = mapped_column(String(32), default="yoomoney")
    payment_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payment_label: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: secrets.token_urlsafe(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="orders")
    plan: Mapped[Plan] = relationship()
    payments: Mapped[list[Payment]] = relationship(back_populates="order")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_status_ends", "status", "ends_at"),
        UniqueConstraint("sub_token", name="uq_subscriptions_sub_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.trial)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    traffic_limit_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traffic_used_gb: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("0"))
    device_limit: Mapped[int] = mapped_column(Integer, default=2)
    sub_token: Mapped[str] = mapped_column(String(64), default=_sub_token, index=True)
    marzban_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    marzban_uuid: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="subscriptions")
    plan: Mapped[Plan | None] = relationship()


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_payments_provider_external"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="payments")


class VpnNode(Base):
    __tablename__ = "vpn_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    marzban_node_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[int] = mapped_column(Integer, default=100)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_users: Mapped[int] = mapped_column(Integer, default=0)
