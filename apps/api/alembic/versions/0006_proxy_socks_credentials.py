"""proxy_access per-user SOCKS5 credentials

Revision ID: 0006_proxy_socks
Revises: 0005_proxy_access
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_proxy_socks"
down_revision = "0005_proxy_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proxy_access", sa.Column("socks_username", sa.String(length=64), nullable=True))
    op.add_column("proxy_access", sa.Column("socks_password", sa.String(length=128), nullable=True))
    op.create_index("ix_proxy_access_socks_username", "proxy_access", ["socks_username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_proxy_access_socks_username", table_name="proxy_access")
    op.drop_column("proxy_access", "socks_password")
    op.drop_column("proxy_access", "socks_username")
