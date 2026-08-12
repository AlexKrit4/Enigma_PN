"""proxy_access for MTProto tariff

Revision ID: 0005_proxy_access
Revises: 0004_order_meta_nullable_plan
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_proxy_access"
down_revision = "0004_order_meta_nullable_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proxy_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "trial",
                "active",
                "expired",
                "disabled",
                name="subscriptionstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_proxy_access_user_id", "proxy_access", ["user_id"], unique=True)
    op.create_index("ix_proxy_access_status_ends", "proxy_access", ["status", "ends_at"])


def downgrade() -> None:
    op.drop_index("ix_proxy_access_status_ends", table_name="proxy_access")
    op.drop_index("ix_proxy_access_user_id", table_name="proxy_access")
    op.drop_table("proxy_access")
