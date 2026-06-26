"""referral: реферальная система

Revision ID: referral
Revises: promo_v2
Create Date: 2026-06-26 14:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "referral"
down_revision = "promo_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("referred_by", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("referral_rewarded", sa.Boolean(), server_default="false", nullable=False))
    # Настройка по умолчанию: 1 день бонуса за реферала
    op.execute("INSERT INTO bot_settings (key, value) VALUES ('referral_bonus_days', '1') ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_column("users", "referral_rewarded")
    op.drop_column("users", "referred_by")
    op.execute("DELETE FROM bot_settings WHERE key = 'referral_bonus_days'")
