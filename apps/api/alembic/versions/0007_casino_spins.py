"""casino_spins ledger for Mini App slot

Revision ID: 0007_casino_spins
Revises: 0006_proxy_socks
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_casino_spins"
down_revision = "0006_proxy_socks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "casino_spins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subscriptions.id"),
            nullable=False,
        ),
        sa.Column("bet_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("win_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("net_days", sa.Integer(), nullable=False, server_default="-1"),
        sa.Column("grid", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "winning_lines", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_casino_spins_user_id", "casino_spins", ["user_id"])
    op.create_index("ix_casino_spins_subscription_id", "casino_spins", ["subscription_id"])
    op.create_index("ix_casino_spins_user_created", "casino_spins", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_casino_spins_user_created", table_name="casino_spins")
    op.drop_index("ix_casino_spins_subscription_id", table_name="casino_spins")
    op.drop_index("ix_casino_spins_user_id", table_name="casino_spins")
    op.drop_table("casino_spins")
