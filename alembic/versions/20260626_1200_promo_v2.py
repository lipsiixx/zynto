"""promo_v2: multi-use и скидочные промокоды

Revision ID: promo_v2
Revises: 843870b795d8
Create Date: 2026-06-26 12:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "promo_v2"
down_revision = "843870b795d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("promo_codes", sa.Column("code_type", sa.String(20), server_default="access", nullable=False))
    op.add_column("promo_codes", sa.Column("discount_stars", sa.Integer(), nullable=True))
    op.add_column("promo_codes", sa.Column("discount_tariff_id", sa.BigInteger(), nullable=True))
    op.add_column("promo_codes", sa.Column("max_uses", sa.Integer(), server_default="1", nullable=True))
    op.add_column("promo_codes", sa.Column("uses_count", sa.Integer(), server_default="0", nullable=False))
    # Для старых записей где used_by заполнен — проставляем uses_count=1
    op.execute("UPDATE promo_codes SET uses_count = 1 WHERE used_by IS NOT NULL")
    op.add_column("users", sa.Column("pending_promo_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "pending_promo_id")
    op.drop_column("promo_codes", "uses_count")
    op.drop_column("promo_codes", "max_uses")
    op.drop_column("promo_codes", "discount_tariff_id")
    op.drop_column("promo_codes", "discount_stars")
    op.drop_column("promo_codes", "code_type")
