"""promo codes

Revision ID: 0002_promo_codes
Revises: 0001_initial
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_promo_codes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("traffic_gb", sa.Integer(), nullable=True),
        sa.Column("device_limit", sa.Integer(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"])

    op.create_table(
        "promo_redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("promo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("promo_codes.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("promo_id", "user_id", name="uq_promo_user"),
    )
    op.create_index("ix_promo_redemptions_promo_id", "promo_redemptions", ["promo_id"])
    op.create_index("ix_promo_redemptions_user_id", "promo_redemptions", ["user_id"])


def downgrade() -> None:
    op.drop_table("promo_redemptions")
    op.drop_table("promo_codes")
