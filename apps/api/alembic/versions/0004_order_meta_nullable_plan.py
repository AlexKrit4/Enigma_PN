"""order meta + nullable plan_id

Revision ID: 0004_order_meta_nullable_plan
Revises: 0003_subscription_devices
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_order_meta_nullable_plan"
down_revision = "0003_subscription_devices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("orders", "plan_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column(
        "orders",
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("orders", "meta")
    op.alter_column("orders", "plan_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
