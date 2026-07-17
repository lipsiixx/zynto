"""history_retention_hours: персональная настройка окна видимости истории/уведомлений в users

Revision ID: history_retention_hours
Revises: view_once_flag
Create Date: 2026-07-17 10:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "history_retention_hours"
down_revision = "view_once_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "history_retention_hours",
            sa.Integer(),
            nullable=False,
            server_default="48",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "history_retention_hours")
