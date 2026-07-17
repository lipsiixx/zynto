"""history_cleared_at: персональный cutoff «очистить всю историю» в мини-аппе

Revision ID: history_cleared_at
Revises: history_retention_hours
Create Date: 2026-07-18 10:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "history_cleared_at"
down_revision = "history_retention_hours"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "history_cleared_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "history_cleared_at")
