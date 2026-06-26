"""nudge: подначивающие сообщения для истёкших подписок

Revision ID: nudge
Revises: referral
Create Date: 2026-06-26 16:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP

revision = "nudge"
down_revision = "referral"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nudge_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.add_column("users", sa.Column("nudge_sent_at", TIMESTAMP(timezone=True), nullable=True))
    op.add_column("users", sa.Column("nudge_next_at", TIMESTAMP(timezone=True), nullable=True))
    op.create_index("ix_users_nudge_next_at", "users", ["nudge_next_at"])
    op.execute(
        "INSERT INTO bot_settings (key, value) VALUES "
        "('nudge_enabled', '0'), "
        "('nudge_interval_days', '1'), "
        "('nudge_grace_days', '3') "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM bot_settings WHERE key IN "
        "('nudge_enabled', 'nudge_interval_days', 'nudge_grace_days')"
    )
    op.drop_index("ix_users_nudge_next_at", "users")
    op.drop_column("users", "nudge_next_at")
    op.drop_column("users", "nudge_sent_at")
    op.drop_table("nudge_messages")
