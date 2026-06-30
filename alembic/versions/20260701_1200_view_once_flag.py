"""view_once_flag: is_view_once в messages_log

Revision ID: view_once_flag
Revises: network_fields
Create Date: 2026-07-01 12:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "view_once_flag"
down_revision = "network_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages_log",
        sa.Column("is_view_once", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("messages_log", "is_view_once")
