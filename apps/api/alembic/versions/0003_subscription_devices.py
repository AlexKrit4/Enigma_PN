"""subscription devices

Revision ID: 0003_subscription_devices
Revises: 0002_promo_codes
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_subscription_devices"
down_revision = "0002_promo_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hwid", sa.String(128), nullable=False),
        sa.Column("device_os", sa.String(64), nullable=True),
        sa.Column("device_model", sa.String(128), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("subscription_id", "hwid", name="uq_subscription_device_hwid"),
    )
    op.create_index("ix_subscription_devices_subscription_id", "subscription_devices", ["subscription_id"])
    op.create_index("ix_subscription_devices_hwid", "subscription_devices", ["hwid"])


def downgrade() -> None:
    op.drop_table("subscription_devices")
