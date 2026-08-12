"""casino pending bet days for feature buys

Revision ID: 0010_casino_pending_bet
Revises: 0009_casino_god_mode
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_casino_pending_bet"
down_revision = "0009_casino_god_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "casino_pending_bet_days",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "casino_pending_bet_days")
