"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("referral_code", sa.String(16), nullable=False),
        sa.Column("referred_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("telegram_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("referral_code"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("group_name", sa.String(64), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("traffic_gb", sa.Integer(), nullable=True),
        sa.Column("device_limit", sa.Integer(), nullable=False),
        sa.Column("price_rub", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_stars", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_plans_slug", "plans", ["slug"])

    op.create_table(
        "vpn_nodes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("marzban_node_url", sa.Text(), nullable=True),
        sa.Column("weight", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("current_users", sa.Integer(), server_default="0", nullable=False),
    )

    # create_type=False — enums are created once below; avoids DuplicateObjectError
    order_status = postgresql.ENUM(
        "pending", "paid", "failed", "refunded", name="orderstatus", create_type=False
    )
    sub_status = postgresql.ENUM(
        "trial", "active", "expired", "disabled", name="subscriptionstatus", create_type=False
    )
    order_status.create(op.get_bind(), checkfirst=True)
    sub_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("payment_provider", sa.String(32), nullable=False),
        sa.Column("payment_external_id", sa.String(128), nullable=True),
        sa.Column("payment_label", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("payment_label"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_payment_external_id", "orders", ["payment_external_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("status", sub_status, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("traffic_limit_gb", sa.Integer(), nullable=True),
        sa.Column("traffic_used_gb", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.Column("device_limit", sa.Integer(), nullable=False),
        sa.Column("sub_token", sa.String(64), nullable=False),
        sa.Column("marzban_username", sa.String(128), nullable=True),
        sa.Column("marzban_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("node_id", sa.String(64), nullable=True),
        sa.Column("reminder_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.UniqueConstraint("sub_token", name="uq_subscriptions_sub_token"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_sub_token", "subscriptions", ["sub_token"])
    op.create_index("ix_subscriptions_status_ends", "subscriptions", ["status", "ends_at"])

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("provider", "external_id", name="uq_payments_provider_external"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("subscriptions")
    op.drop_table("orders")
    op.drop_table("vpn_nodes")
    op.drop_table("plans")
    op.drop_table("users")
    sa.Enum(name="subscriptionstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="orderstatus").drop(op.get_bind(), checkfirst=True)
