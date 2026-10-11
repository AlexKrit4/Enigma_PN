"""casino god mode pending flag on users

Revision ID: 0009_casino_god_mode
Revises: 0008_casino_bonus_buy
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_casino_god_mode"
down_revision = "0008_casino_bonus_buy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "casino_god_mode_pending",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "casino_god_mode_pending")
