"""network_fields: network_visible и network_consent_at в users

Revision ID: network_fields
Revises: referral_rewards
Create Date: 2026-06-30 15:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "network_fields"
down_revision = "referral_rewards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("network_visible", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("network_consent_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "network_consent_at")
    op.drop_column("users", "network_visible")
