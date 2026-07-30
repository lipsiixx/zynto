"""tariff_sale_price: акционная цена тарифа — original_price_stars в tariffs

Revision ID: tariff_sale_price
Revises: history_cleared_at
Create Date: 2026-07-30 12:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "tariff_sale_price"
down_revision = "history_cleared_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tariffs",
        sa.Column(
            "original_price_stars",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tariffs", "original_price_stars")
