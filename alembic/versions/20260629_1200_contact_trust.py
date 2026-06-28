"""contact_trust: кредит доверия к контактам для мини-апп

Revision ID: contact_trust
Revises: nudge_media
Create Date: 2026-06-29 12:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "contact_trust"
down_revision = "nudge_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_trust",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("manual_score", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )
    op.create_index("ix_contact_trust_user_chat", "contact_trust", ["user_id", "chat_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_contact_trust_user_chat", "contact_trust")
    op.drop_table("contact_trust")
