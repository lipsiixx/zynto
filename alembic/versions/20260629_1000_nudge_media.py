"""nudge_media: поддержка фото/видео в подначивающих сообщениях

Revision ID: nudge_media
Revises: api_fields
Create Date: 2026-06-29 10:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "nudge_media"
down_revision = "api_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nudge_messages", sa.Column("media_file_id", sa.Text(), nullable=True))
    op.add_column("nudge_messages", sa.Column("media_type", sa.String(10), nullable=True))
    op.alter_column("nudge_messages", "text", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE nudge_messages SET text = '' WHERE text IS NULL")
    op.alter_column("nudge_messages", "text", nullable=False)
    op.drop_column("nudge_messages", "media_type")
    op.drop_column("nudge_messages", "media_file_id")
