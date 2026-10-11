"""casino bonus buy pending flag on users

Revision ID: 0008_casino_bonus_buy
Revises: 0007_casino_spins
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_casino_bonus_buy"
down_revision = "0007_casino_spins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "casino_bonus_pending",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "casino_bonus_pending")
