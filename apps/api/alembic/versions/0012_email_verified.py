"""email verification for site accounts

Revision ID: 0012_email_verified
Revises: 0011_site_accounts
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_email_verified"
down_revision = "0011_site_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Аккаунты, созданные до введения подтверждения почты, считаем подтверждёнными,
    # чтобы они не потеряли доступ до настройки SMTP.
    op.execute("UPDATE users SET email_verified = true")


def downgrade() -> None:
    op.drop_column("users", "email_verified")
