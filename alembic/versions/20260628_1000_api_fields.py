"""api_fields: phone/avatar в users, content_hash в media_cache

Revision ID: api_fields
Revises: nudge
Create Date: 2026-06-28 10:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "api_fields"
down_revision = "nudge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("avatar_file_id", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("avatar_file_unique_id", sa.String(255), nullable=True))
    op.add_column("media_cache", sa.Column("content_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("media_cache", "content_hash")
    op.drop_column("users", "avatar_file_unique_id")
    op.drop_column("users", "avatar_file_id")
    op.drop_column("users", "phone")
