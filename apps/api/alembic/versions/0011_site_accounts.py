"""site accounts: users.password_hash + website plan

Revision ID: 0011_site_accounts
Revises: 0010_casino_pending_bet
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0011_site_accounts"
down_revision = "0010_casino_pending_bet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.execute(
        sa.text(
            """
            INSERT INTO plans (id, slug, name, group_name, duration_days, traffic_gb, device_limit,
                               price_rub, price_stars, is_active, sort_order)
            SELECT :id, 'site-bypass', 'Обход белых списков', 'сайт', 30, NULL, 5, 200.00, NULL, true, 100
            WHERE NOT EXISTS (SELECT 1 FROM plans WHERE slug = 'site-bypass')
            """
        ).bindparams(id=uuid.uuid4())
    )


def downgrade() -> None:
    op.execute("DELETE FROM plans WHERE slug = 'site-bypass'")
    op.drop_column("users", "password_hash")
